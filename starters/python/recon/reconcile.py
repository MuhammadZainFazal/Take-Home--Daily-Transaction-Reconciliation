from __future__ import annotations

from collections import defaultdict

from .models import (
    AMOUNT_DIFFERS,
    DUPLICATE_ID,
    MISSING_IN_LEDGER,
    MISSING_IN_PROVIDER,
    NO_ID,
    Finding,
    Result,
    Transaction,
)


def _split_by_id_presence(txs: list[Transaction]) -> tuple[dict[str, list[Transaction]], list[Transaction]]:
    by_id: dict[str, list[Transaction]] = defaultdict(list)
    no_id: list[Transaction] = []
    for t in txs:
        if t.id:
            by_id[t.id].append(t)
        else:
            no_id.append(t)
    return by_id, no_id


def _drop_exact_copies(rows: list[Transaction]) -> list[Transaction]:
    """Collapse rows that are identical in every field: the same line repeated."""
    return list(dict.fromkeys(rows))


def reconcile(provider: list[Transaction], ledger: list[Transaction]) -> Result:
    p_by_id, p_no_id = _split_by_id_presence(provider)
    l_by_id, l_no_id = _split_by_id_presence(ledger)
    findings: list[Finding] = []
    matched = 0

    for t in p_no_id + l_no_id:
        findings.append(Finding(NO_ID, f"{NO_ID}:{t.source}:{t.ref}", (t,)))

    for id_ in sorted(p_by_id.keys() | l_by_id.keys()):
        p_rows = p_by_id.get(id_, [])
        l_rows = l_by_id.get(id_, [])

        # Missing takes priority over duplicates: if one side has nothing,
        # that is the fact finance needs, and the record still shows any repeats.
        if not l_rows:
            findings.append(Finding(MISSING_IN_LEDGER, f"{MISSING_IN_LEDGER}:{id_}", tuple(p_rows)))
            continue
        if not p_rows:
            findings.append(Finding(MISSING_IN_PROVIDER, f"{MISSING_IN_PROVIDER}:{id_}", tuple(l_rows)))
            continue

        p_rows = _drop_exact_copies(p_rows)
        l_rows = _drop_exact_copies(l_rows)

        if len(p_rows) > 1 or len(l_rows) > 1:
            # Same ID but different rows: we can't tell which pairs with which, so no guess.
            findings.append(Finding(DUPLICATE_ID, f"{DUPLICATE_ID}:{id_}", tuple(p_rows + l_rows)))
        elif p_rows[0].amount_cents != l_rows[0].amount_cents:
            findings.append(Finding(AMOUNT_DIFFERS, f"{AMOUNT_DIFFERS}:{id_}", (p_rows[0], l_rows[0])))
        else:
            matched += 1

    return Result(findings, matched)
