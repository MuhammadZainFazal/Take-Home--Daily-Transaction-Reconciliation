from __future__ import annotations

from .models import Changes, Transaction


def _fmt(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def _items(count: int) -> str:
    return f"{count:,} item" + ("" if count == 1 else "s")


def render_summary(date: str, provider: list[Transaction], ledger: list[Transaction], matched: int,
                   changes: Changes, still_open: int) -> str:
    # The totals are the sums of the two files exported for this date, to the cent.
    provider_total = sum(t.amount_cents for t in provider)
    ledger_total = sum(t.amount_cents for t in ledger)
    gap = ledger_total - provider_total
    new = len(changes.new)

    if gap == 0:
        higher = ""
    else:
        higher = f"  ({'ledger' if gap > 0 else 'provider'} is higher)"

    # A matching total does not mean every transaction matches: two errors can cancel out.
    if gap == 0 and new == 0:
        note = "No new items need attention."
    elif gap == 0:
        note = (f"The totals match, but {_items(new)} still need attention. Two errors can cancel each "
                "other out, so matching totals do not mean every transaction matches.")
    elif new == 0:
        note = "No new items explain the difference. It may come from items still open from earlier days."
    else:
        note = "The items in the report show where the two sides disagree."

    return "\n".join([
        f"Reconciliation summary for {date}",
        "",
        "Totals match." if gap == 0 else "Totals do NOT match.",
        f"  {'Provider total':<16}{_fmt(provider_total):>14}",
        f"  {'Ledger total':<16}{_fmt(ledger_total):>14}",
        f"  {'Difference':<16}{_fmt(abs(gap)):>14}{higher}",
        "",
        f"Read {len(provider):,} provider rows and {len(ledger):,} ledger rows; {matched:,} matched on ID.",
        f"{_items(new)} to check, {len(changes.resolved):,} resolved since the last run, "
        f"{still_open:,} still open from earlier days (not repeated in the report).",
        note,
        "Totals are the sums of the two files exported for this date. Amounts are in euros.",
    ]) + "\n"
