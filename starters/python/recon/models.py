from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Transaction:
    """One row from either export, normalised to a common shape. See docs/DATA_SPEC.md."""

    source: str          # "provider" or "ledger"
    id: str | None       # transaction id shared by both systems; None when the row has none
    ref: str             # always present: ledger entry_id, provider transaction id, or "file:line"
    amount_cents: int    # whole euro cents, exact
    timestamp: datetime  # timezone-aware, UTC
    merchant: str        # raw string from the source; the two systems never agree textually
    problem: str | None = None  # set when the row holds a value we don't expect (see normalize.py)


# Kinds of finding the reconciliation can produce.
AMOUNT_DIFFERS = "amount_differs"            # same ID on both sides, different amount
MISSING_IN_LEDGER = "missing_in_ledger"      # ID only in provider
MISSING_IN_PROVIDER = "missing_in_provider"  # ID only in ledger
DUPLICATE_ID = "duplicate_id"                # same ID, differing rows, on one side
NO_ID = "no_id"                              # row has no ID, so it cannot be matched
UNEXPECTED_VALUE = "unexpected_value"        # non-EUR currency, status not "captured", negative amount


@dataclass(frozen=True)
class Finding:
    kind: str
    key: str                          # stable across runs: same situation, same key
    records: tuple[Transaction, ...]  # the rows involved, from both sides where relevant


@dataclass(frozen=True)
class Result:
    findings: list[Finding]
    matched: int  # IDs present once on each side with equal amounts


@dataclass(frozen=True)
class Changes:
    new: list[Finding]       # findings that were not open before this run
    resolved: list[Finding]  # findings that were open and no longer apply
