"""recon run --date YYYY-MM-DD"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .models import Finding
from .readers import load_day
from .reconcile import reconcile
from .state import carried_rows, checksum, load, save, update

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_STATE_DIR = REPO_ROOT / "states"


def _eur(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _describe(f: Finding) -> str:
    rows = "; ".join(f"{t.source} {t.ref} EUR {_eur(t.amount_cents)} {t.merchant}" for t in f.records)
    return f"- {f.key} -> {rows}"


def run(date: str, data_dir: Path, state_dir: Path) -> int:
    provider_path = data_dir / f"provider-{date}.jsonl"
    ledger_path = data_dir / f"ledger-{date}.csv"
    state_path = state_dir / "state.json"

    try:
        digest = checksum(provider_path, ledger_path)
    except FileNotFoundError as e:
        print(f"Cannot run {date}: file not found: {e.filename}")
        return 1

    state = load(state_path)

    # Re-run guard: a date we have already processed is never processed twice.
    previous = state["runs"].get(date)
    if previous is not None:
        if previous["checksum"] == digest:
            print(f"{date} was already processed. Nothing new.")
            return 0
        print(f"{date} was already processed, but its input files have changed since. "
              "Not reprocessing; someone needs to decide how to handle a corrected export.")
        return 1

    provider, ledger = load_day(data_dir, date)
    print(f"{date}: {len(provider)} provider records, {len(ledger)} ledger rows")

    # Compare today's rows together with rows from still-open findings,
    # so a row that was missing yesterday can be found on the other side today.
    carried_p, carried_l = carried_rows(state)
    pool_p = list(dict.fromkeys(carried_p + provider))  # dict.fromkeys drops repeats, keeps order
    pool_l = list(dict.fromkeys(carried_l + ledger))

    result = reconcile(pool_p, pool_l)
    changes = update(state, date, result.findings)
    state["runs"][date] = {"checksum": digest}
    save(state_path, state)  # one write at the end: a failed run leaves no trace

    # Temporary plain dump
    print(f"Matched on ID, same amount: {result.matched}")
    print(f"New findings: {len(changes.new)}")
    for f in changes.new:
        print(_describe(f))
    print(f"Resolved since last run: {len(changes.resolved)}")
    for f in changes.resolved:
        print(_describe(f))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="recon")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run", help="reconcile one day")
    p_run.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_run.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p_run.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    args = parser.parse_args(argv)
    if args.command == "run":
        return run(args.date, args.data_dir, args.state_dir)
    return 2


if __name__ == "__main__":
    sys.exit(main())
