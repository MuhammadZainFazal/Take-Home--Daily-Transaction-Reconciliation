# Daily transaction reconciliation

Compares the payment provider's daily export with the internal ledger and tells finance what does not match. It is run once a day and reports only what changed since the previous run.

## What it does

- Reports transactions that are on one side only, and transactions on both sides with different amounts.
- Reports only what changed: new discrepancies, and ones that have since resolved. State is kept between runs.
- Is safe to re-run. Running the same date twice produces nothing new and leaves the state untouched.
- Never guesses. Rows it cannot match with certainty (no transaction ID, a repeated ID, an unexpected value) are flagged for a person to look at.

## Running it

Python 3.11 or newer, standard library only.

```
cd starters/python
python -m recon run --date 2026-03-01
python -m recon run --date 2026-03-02
```

On Windows, install the time zone database once: `pip install tzdata`. Python reads time zones from the operating system, and Windows does not provide them; macOS and Linux need nothing.

| Option | Default | Meaning |
|---|---|---|
| `--data-dir` | `data/` | where the daily exports are |
| `--state-dir` | `states/` | where `state.json` is kept |
| `--report-dir` | `reports/` | where the CSV reports are written |

Each run writes `reports/report-DATE.csv`, updates `states/state.json`, and prints a short summary (rows read, matched, new items, resolved, still open). Run dates in order.

Tests: `python -m unittest` from `starters/python`. There are ten small ones: each matching rule once, plus re-running a date, the next day reporting only changes, and refusing changed files.

If a date has already been processed with the same files, the tool says so and does nothing. If the files for that date have changed since, it refuses and says why (see question 7 in `docs/QUESTIONS.md`).

## How it works

Rows are matched on the transaction ID and nothing else. Amount, time and merchant are never used to pair rows, because any of them can legitimately differ between the two systems.

| Situation | What the report says |
|---|---|
| ID on both sides, same amount | Nothing. It is counted as matched. |
| ID on both sides, different amount | Amount differs |
| ID only at the provider / only in the ledger | Missing in ledger / Missing at provider |
| Same ID on several different rows of one side | Appears more than once |
| No transaction ID, either side | No transaction ID (check by hand) |
| Currency not EUR, status not "captured", negative amount | Unexpected value (left out of matching) |

**State.** `states/state.json` holds every finding ever raised, with a status of open or resolved. Open findings keep their rows, so the next run compares them with the next day's files: something missing today can resolve tomorrow. Each run recomputes the findings and compares them with what is stored, so only new and resolved ones are reported. A checksum of each date's input files stops a date being processed twice. The state file is written once, at the end of a successful run.

**Reading the report.** It is a CSV for Excel: one row per record, except that the two sides of an amount difference share a row. Columns are Status, Issue, Transaction ID, Time (Amsterdam), Merchant, Provider ref, Provider amount, Ledger ref, Ledger amount, Difference, Note. A real example is in `docs/sample_report-2026-03-01.csv`.

**Day 1 result.** 1,986 provider rows and 1,986 ledger rows. 1,953 matched. 59 findings (61 CSV rows): 5 amount differences, 1 repeated ID, 7 missing in the ledger, 9 missing at the provider, 37 rows with no ID.

## Repository layout

```
data/                          the daily exports
docs/DATA_SPEC.md              provided: file formats and normalisation rules
docs/DECISIONS.md              ambiguities found, what was decided, what was rejected
docs/QUESTIONS.md              what to confirm with a real person before go-live
docs/sample_report-...csv      a real report
starters/python/recon/
  readers.py, normalize.py     read and normalise the exports (from the starter)
  models.py                    Transaction, Finding, Result, Changes
  reconcile.py                 the comparison: a pure function, no files or state
  state.py                     the JSON state, the diff, the re-run guard
  report.py                    writes the CSV
  cli.py                       ties the steps together
starters/python/tests/         the small test suite
states/, reports/              created at run time
```

## Where to read more

- `docs/DECISIONS.md` for the ambiguities in the data and the reasoning behind each choice.
- `docs/QUESTIONS.md` for what should be confirmed before this goes live, and what the tool does until it is.

## With another day

- More tests. The suite covers the basics only: not unreadable input, the report layout, or a resolved finding that comes back.
- Put the summary counts into the deliverable. A quiet day currently produces a header-only CSV, and the counts only appear on the console.
- Ask finance which Excel locale they use. A comma-delimited CSV opens in one column in Dutch-language Excel; the delimiter is a single constant in `report.py`.
- A "possible counterpart" hint on rows without an ID: a suggestion for the person, never a match.
- A way to mark an item as dealt with, so it does not sit open forever (the idea behind FIN-124), and a periodic list of everything still open.
- A clear message naming the row when an input row cannot be read, instead of an error.

## How I used AI

I used Claude throughout, as a sparring partner and for drafting, and kept the decisions and the review myself.

- **Brainstorming.** Before writing code I compared ways to match rows, store state and shape the report, and dropped the options that were too complicated or rested on guesses.
- **Where I overrode it.** Claude proposed matching rows without an ID on amount, time and merchant, with a merchant mapping learned from the data. I rejected that: any of the three can legitimately differ, so those rows go to a person. The ordering of the duplicate and missing checks, and the rule for what counts as a repeated row, were my calls. Moving the report from the console to a CSV file was my idea.
- **Refactoring.** After review I had the code simplified, for example removing a redundant de-duplication step and cutting the report down to what finance needs.
- **Verification.** I read every change before integrating it, kept in check diff between steps, and committed in small steps. Changes were checked against the provided data and small throwaway scenarios, and the basics are now covered by a small test suite. The tests were checked by deliberately breaking the code in a few ways (for example removing the re-run guard) to confirm they fail.
- **Documentation.** Claude helped with the structure and wording of these documents. The content reflects the decisions above.

## Future tickets

FIN-121 ("does the total for yesterday match or not") is built on its own branch, `feature/fin-121`. The pull request explains how I read the ticket, what I would have asked Sanne, and why I picked it over the others.