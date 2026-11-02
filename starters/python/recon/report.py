from __future__ import annotations

import csv
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import (
    AMOUNT_DIFFERS,
    DUPLICATE_ID,
    MISSING_IN_LEDGER,
    MISSING_IN_PROVIDER,
    NO_ID,
    UNEXPECTED_VALUE,
    Changes,
    Finding,
    Transaction,
)

LOCAL_TZ = ZoneInfo("Europe/Amsterdam")
DELIMITER = ","

HEADER = ["Status", "Issue", "Transaction ID", "Time (Amsterdam)", "Merchant",
          "Provider ref", "Provider amount", "Ledger ref", "Ledger amount", "Difference", "Note"]

# kind, text for the Issue column, text for the Note column. This is also the order of rows.
ISSUES = [
    (AMOUNT_DIFFERS, "Amount differs", ""),  # the note says which side is higher
    (DUPLICATE_ID, "Appears more than once",
     "Same transaction ID on more than one row. Check for a double charge or double booking."),
    (MISSING_IN_LEDGER, "Missing in ledger",
     "At the provider but not in the ledger. It may just not be booked yet."),
    (MISSING_IN_PROVIDER, "Missing at provider",
     "In the ledger but not at the provider."),
    (NO_ID, "No transaction ID",
     "Cannot be matched automatically. Check by hand."),
    (UNEXPECTED_VALUE, "Unexpected value",
     "Left out of matching, so the other side may show as missing."),
]
ISSUE = {kind: (title, note) for kind, title, note in ISSUES}
ORDER = {kind: i for i, (kind, _, _) in enumerate(ISSUES)}


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100}.{abs(cents) % 100:02d}"  # plain number, so Excel can sum it


def _rows(status: str, f: Finding) -> list[list[str]]:
    title, note = ISSUE[f.kind]
    # One row per record, except an amount difference: its two records share one row.
    groups = [list(f.records)] if f.kind == AMOUNT_DIFFERS else [[t] for t in f.records]
    rows = []
    for group in groups:
        p = next((t for t in group if t.source == "provider"), None)
        l = next((t for t in group if t.source == "ledger"), None)
        first = p or l
        row_note = f"{first.problem[0].upper()}{first.problem[1:]}. {note}" if first.problem else note
        difference = ""
        if f.kind == AMOUNT_DIFFERS:
            gap = l.amount_cents - p.amount_cents
            difference = _money(abs(gap))
            row_note = "Ledger is higher" if gap > 0 else "Provider is higher"
        rows.append([
            status,
            title,
            first.id or "",
            first.timestamp.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            (l or p).merchant,
            p.ref if p else "",
            _money(p.amount_cents) if p else "",
            l.ref if l else "",
            _money(l.amount_cents) if l else "",
            difference,
            row_note,
        ])
    return rows


def build_rows(changes: Changes) -> list[list[str]]:
    rows: list[list[str]] = []
    for status, findings in (("New", changes.new), ("Resolved", changes.resolved)):
        for f in sorted(findings, key=lambda f: (ORDER[f.kind], f.records[0].timestamp)):
            rows += _rows(status, f)
    return rows


def write_csv(path: Path, changes: Changes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig adds a marker that tells Excel the file is UTF-8.
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=DELIMITER)
        writer.writerow(HEADER)
        writer.writerows(build_rows(changes))
