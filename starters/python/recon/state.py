from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from .models import Changes, Finding, Transaction


def load(path: Path) -> dict:
    if not path.exists():
        return {"runs": {}, "findings": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, state: dict) -> None:
    """Write to a temp file, then rename, so a crash never leaves a half-written state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def checksum(*paths: Path) -> str:
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes())
    return h.hexdigest()


def _tx_to_dict(t: Transaction) -> dict:
    return {
        "source": t.source,
        "id": t.id,
        "ref": t.ref,
        "amount_cents": t.amount_cents,
        "timestamp": t.timestamp.isoformat(),
        "merchant": t.merchant,
        "problem": t.problem,
    }


def _tx_from_dict(d: dict) -> Transaction:
    return Transaction(
        source=d["source"],
        id=d["id"],
        ref=d["ref"],
        amount_cents=d["amount_cents"],
        timestamp=datetime.fromisoformat(d["timestamp"]),
        merchant=d["merchant"],
        problem=d.get("problem"),
    )


def _finding_from_entry(key: str, entry: dict) -> Finding:
    return Finding(entry["kind"], key, tuple(_tx_from_dict(r) for r in entry["records"]))


def carried_rows(state: dict) -> tuple[list[Transaction], list[Transaction]]:
    """Rows belonging to still-open findings, split by side, to be compared again today."""
    provider: list[Transaction] = []
    ledger: list[Transaction] = []
    for entry in state["findings"].values():
        if entry["status"] != "open":
            continue
        for d in entry["records"]:
            t = _tx_from_dict(d)
            (provider if t.source == "provider" else ledger).append(t)
    return provider, ledger


def update(state: dict, date: str, current: list[Finding]) -> Changes:
    """Compare today's findings with what is stored. Mutates state; returns only what changed."""
    stored = state["findings"]
    current_by_key = {f.key: f for f in current}
    new: list[Finding] = []
    resolved: list[Finding] = []

    for key, f in sorted(current_by_key.items()):
        entry = stored.get(key)
        records = [_tx_to_dict(t) for t in f.records]
        if entry is None or entry["status"] == "resolved":
            # Never seen, or it was resolved and has come back: report it as new.
            stored[key] = {
                "kind": f.kind,
                "status": "open",
                "first_seen": date,
                "resolved_on": None,
                "records": records,
            }
            new.append(f)
        else:
            entry["records"] = records  # still open: refresh quietly, nothing to report

    for key, entry in sorted(stored.items()):
        if entry["status"] == "open" and key not in current_by_key:
            entry["status"] = "resolved"
            entry["resolved_on"] = date
            resolved.append(_finding_from_entry(key, entry))

    return Changes(new, resolved)
