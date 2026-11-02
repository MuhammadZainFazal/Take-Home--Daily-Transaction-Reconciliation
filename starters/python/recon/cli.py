"""recon run --date YYYY-MM-DD"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .readers import load_day
from .report import write_csv
from .summary import render_summary
from .reconcile import reconcile
from .state import carried_rows, checksum, load, save, update

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_STATE_DIR = REPO_ROOT / "states"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports"


def run(date: str, data_dir: Path, state_dir: Path, report_dir: Path) -> int:
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

    # Compare today's rows together with rows from still-open findings,
    # so a row that was missing yesterday can be found on the other side today.
    # A row present in both lists is collapsed inside reconcile and update.
    carried_p, carried_l = carried_rows(state)
    result = reconcile(carried_p + provider, carried_l + ledger)
    changes = update(state, date, result.findings)
    state["runs"][date] = {"checksum": digest}

    open_total = sum(1 for e in state["findings"].values() if e["status"] == "open")
    still_open = open_total - len(changes.new)  # open before today, not repeated in the report
    report_path = report_dir / f"report-{date}.csv"
    write_csv(report_path, changes)
    summary = render_summary(date, provider, ledger, result.matched, changes, still_open)
    (report_dir / f"summary-{date}.txt").write_text(summary, encoding="utf-8")

    # State is saved last: if anything above failed, the date is not marked as processed
    # and can simply be run again.
    save(state_path, state)

    print(summary)
    print(f"Report: {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="recon")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run", help="reconcile one day")
    p_run.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_run.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p_run.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    p_run.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args(argv)
    if args.command == "run":
        return run(args.date, args.data_dir, args.state_dir, args.report_dir)
    return 2


if __name__ == "__main__":
    sys.exit(main())
