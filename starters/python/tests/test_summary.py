import unittest
from datetime import datetime, timezone

from recon.models import Changes, Transaction
from recon.reconcile import reconcile
from recon.summary import render_summary


def tx(source, id_, cents, ref=None):
    ts = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
    return Transaction(source, id_, ref or id_, cents, ts, "SHOP")


class TotalsSummary(unittest.TestCase):
    def summary(self, provider, ledger):
        result = reconcile(provider, ledger)
        return render_summary("2026-03-01", provider, ledger, result.matched, Changes(result.findings, []), 0)

    def test_totals_that_differ_say_so_and_give_the_difference(self):
        text = self.summary([tx("provider", "a", 1000)], [tx("ledger", "a", 1500, "LG-1")])
        self.assertIn("Totals do NOT match.", text)
        self.assertIn("5.00  (ledger is higher)", text)

    def test_matching_totals_do_not_hide_items_that_need_attention(self):
        # two errors that cancel out: the totals agree, yet neither transaction matches
        provider = [tx("provider", "a", 1000), tx("provider", "b", 2000)]
        ledger = [tx("ledger", "a", 2000, "LG-1"), tx("ledger", "b", 1000, "LG-2")]
        text = self.summary(provider, ledger)
        self.assertIn("Totals match.", text)
        self.assertIn("but 2 items still need attention", text)


if __name__ == "__main__":
    unittest.main()
