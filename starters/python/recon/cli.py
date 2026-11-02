"""recon run --date YYYY-MM-DD"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .readers import load_day
from .reconcile import reconcile

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _eur(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def run(date: str, data_dir: Path) -> int:
    provider, ledger = load_day(data_dir, date)
    print(f"{date}: {len(provider)} provider records, {len(ledger)} ledger rows")

    result = reconcile(provider, ledger)
    print(f"Matched on ID, same amount: {result.matched}")
    print(f"Findings: {len(result.findings)}")
    for kind, n in sorted(Counter(f.kind for f in result.findings).items()):
        print(f"  {kind}: {n}")

    # Temporary plain dump
    for f in sorted(result.findings, key=lambda f: f.key):
        rows = "; ".join(f"{t.source} {t.ref} EUR {_eur(t.amount_cents)} {t.merchant}" for t in f.records)
        print(f"- {f.key} -> {rows}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="recon")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run", help="reconcile one day")
    p_run.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_run.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args(argv)
    if args.command == "run":
        return run(args.date, args.data_dir)
    return 2


if __name__ == "__main__":
    sys.exit(main())
