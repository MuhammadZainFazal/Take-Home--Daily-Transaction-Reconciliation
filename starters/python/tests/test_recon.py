import contextlib
import csv
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from recon.cli import run
from recon.models import (
    AMOUNT_DIFFERS,
    DUPLICATE_ID,
    MISSING_IN_LEDGER,
    MISSING_IN_PROVIDER,
    NO_ID,
    UNEXPECTED_VALUE,
    Transaction,
)
from recon.normalize import normalize_provider
from recon.reconcile import reconcile


def tx(source, id_, amount=1000, second=0, ref=None, problem=None):
    ref = ref or id_ or f"{source}-{second}"
    ts = datetime(2026, 3, 1, 10, 0, second, tzinfo=timezone.utc)
    return Transaction(source, id_, ref, amount, ts, "SHOP", problem)


def kinds(result):
    return sorted(f.kind for f in result.findings)


class ReconcileRules(unittest.TestCase):
    def test_same_id_same_amount_is_matched(self):
        r = reconcile([tx("provider", "a")], [tx("ledger", "a", ref="LG-1")])
        self.assertEqual(r.matched, 1)
        self.assertEqual(r.findings, [])

    def test_same_id_different_amount(self):
        r = reconcile([tx("provider", "a", 1957)], [tx("ledger", "a", 19570, ref="LG-1")])
        self.assertEqual(kinds(r), [AMOUNT_DIFFERS])

    def test_id_on_one_side_only(self):
        r = reconcile([tx("provider", "a")], [tx("ledger", "b", ref="LG-1")])
        self.assertEqual(kinds(r), [MISSING_IN_LEDGER, MISSING_IN_PROVIDER])

    def test_missing_outranks_repeated(self):
        r = reconcile([tx("provider", "a"), tx("provider", "a", second=4)], [])
        self.assertEqual(kinds(r), [MISSING_IN_LEDGER])

    def test_repeated_rows(self):
        led = [tx("ledger", "a", ref="LG-1")]
        # identical in every field: one line repeated, so it still matches
        self.assertEqual(reconcile([tx("provider", "a")] * 2, led).matched, 1)
        # same amount but 4 seconds apart: could be a double capture
        r = reconcile([tx("provider", "a"), tx("provider", "a", second=4)], led)
        self.assertEqual(kinds(r), [DUPLICATE_ID])
        # two ledger entries with different entry IDs are two bookings
        r = reconcile([tx("provider", "a")], [tx("ledger", "a", ref="LG-1"), tx("ledger", "a", ref="LG-2")])
        self.assertEqual(kinds(r), [DUPLICATE_ID])

    def test_rows_without_id_are_never_matched(self):
        # same amount, same time: still not paired, because there is no ID to go on
        r = reconcile([tx("provider", None)], [tx("ledger", None, ref="LG-1")])
        self.assertEqual(r.matched, 0)
        self.assertEqual(kinds(r), [NO_ID, NO_ID])

    def test_unexpected_value_is_flagged_and_not_matched(self):
        raw = {"transaction_id": "a", "amount_cents": 1000, "currency": "USD",
               "captured_at": "2026-03-01T10:00:00Z", "merchant": "SHOP", "status": "captured"}
        r = reconcile([normalize_provider(raw, "f:1")], [tx("ledger", "a", ref="LG-1")])
        self.assertEqual(r.matched, 0)
        self.assertEqual(kinds(r), [MISSING_IN_PROVIDER, UNEXPECTED_VALUE])


LEDGER_HEADER = "entry_id,transaction_id,booked_at,amount,merchant,cost_centre\r\n"


class RunAcrossDays(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.data, self.states, self.reports = root / "data", root / "states", root / "reports"
        self.data.mkdir()

    def write_day(self, date, provider=(), ledger=()):
        """provider: (id, cents) pairs; ledger: (entry_id, id, euros) triples."""
        lines = [json.dumps({"transaction_id": i, "amount_cents": c, "currency": "EUR",
                             "captured_at": f"{date}T10:00:00Z", "merchant": "SHOP", "status": "captured"})
                 for i, c in provider]
        (self.data / f"provider-{date}.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""))
        rows = [f"{e},{i},{date} 11:00:30,{a},Shop BV,CC-1\r\n" for e, i, a in ledger]
        (self.data / f"ledger-{date}.csv").write_text(LEDGER_HEADER + "".join(rows), newline="")

    def run_day(self, date):
        with contextlib.redirect_stdout(io.StringIO()):
            return run(date, self.data, self.states, self.reports)

    def report(self, date):
        with open(self.reports / f"report-{date}.csv", newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def test_rerunning_a_date_changes_nothing(self):
        self.write_day("2026-03-01", provider=[("pt_b", 200)])
        self.assertEqual(self.run_day("2026-03-01"), 0)
        before = (self.states / "state.json").read_bytes()
        self.assertEqual(self.run_day("2026-03-01"), 0)
        self.assertEqual((self.states / "state.json").read_bytes(), before)
        self.assertEqual(len(self.report("2026-03-01")), 1)

    def test_next_day_reports_only_what_changed(self):
        self.write_day("2026-03-01", provider=[("pt_b", 200), ("pt_c", 300)], ledger=[("LG-3", "pt_c", "3.50")])
        self.write_day("2026-03-02", ledger=[("LG-2", "pt_b", "2.00")])
        self.run_day("2026-03-01")
        self.assertEqual({r["Issue"] for r in self.report("2026-03-01")}, {"Missing in ledger", "Amount differs"})
        self.run_day("2026-03-02")
        rows = self.report("2026-03-02")
        # pt_b is resolved; pt_c's amount difference is still open but not listed again
        self.assertEqual([(r["Status"], r["Issue"], r["Transaction ID"]) for r in rows],
                         [("Resolved", "Missing in ledger", "pt_b")])
        state = json.loads((self.states / "state.json").read_text())["findings"]
        self.assertEqual(state["missing_in_ledger:pt_b"]["status"], "resolved")
        self.assertEqual(state["amount_differs:pt_c"]["status"], "open")
        # and a day later there is nothing to say: resolved items are not reported again
        self.write_day("2026-03-03")
        self.run_day("2026-03-03")
        self.assertEqual(self.report("2026-03-03"), [])

    def test_changed_files_for_a_processed_date_are_refused(self):
        self.write_day("2026-03-01", provider=[("pt_b", 200)])
        self.run_day("2026-03-01")
        self.write_day("2026-03-01", provider=[("pt_b", 250)])
        self.assertEqual(self.run_day("2026-03-01"), 1)


if __name__ == "__main__":
    unittest.main()
