# Decisions

What was unclear, what I did about it, and what I rejected. Where a decision depends on an answer from a real person, the matching question is in `QUESTIONS.md`.

## What the first day of data showed

| Observation | Why it matters |
|---|---|
| 1,986 rows on each side, but the totals differ (provider 103,851.86, ledger 104,210.02) | Equal row counts hide offsetting differences. |
| 19 provider rows and 18 ledger rows have no transaction ID | They cannot be matched on an identifier. |
| One provider ID appears twice, 4 seconds apart, same amount; the ledger has it once | Possible double capture, possible export artifact. |
| 5 IDs on both sides with different amounts. One is 19.57 against 195.70; the others look like digit slips (19.42 against 19.24) | Reported, not corrected. |
| 7 IDs only at the provider, 9 only in the ledger | The core of the report. |
| Three rows in the ledger file for 1 March were booked after midnight UTC (01:00 local on 2 March) | The spec says each export covers its own date, so the ledger's day rule is unclear. |
| The merchant text never matches between systems | Cannot be used as a key. |

## Decisions

### 1. Match on the transaction ID only

Rows with an ID on both sides are matched. Rows without an ID are never matched; they go to a person.

*Rejected: matching on amount, time and merchant,* possibly with a merchant mapping learned from rows that do share an ID. Any of the three can legitimately differ, and a learned mapping can be wrong in exactly the cases that matter. Day 1 shows why a rule would be a guess: one provider row for 249.00 with no ID has two possible ledger rows, 25 and 115 seconds later, and the rows without an ID lagged by up to about two and a half minutes against 90 seconds for those with one. A wrong match hides a real discrepancy; an unmatched row costs a person a minute. See question 8.

### 2. "Missing" outranks "repeated"

If an ID is absent on one side, that is reported as missing even when the other side holds several rows. It is the fact finance needs first, and the finding still lists every row.

### 3. What counts as a repeated row

On one side, rows identical in every field are one line repeated and are collapsed. Anything else with the same ID is flagged as appearing more than once: a different timestamp (the Google Cloud pair on day 1), a different merchant text, or, on the ledger, a different entry ID, which is a separate booking. Silently collapsing the last two would hide a possible double booking. See question 4.

### 4. Amount differences are reported, not resolved

Both amounts, the difference and which side is higher are shown. The tool does not decide which side is right, because nothing in the brief says. See question 5.

### 5. Rows with unexpected values are flagged and kept out of matching

A provider row with a currency other than EUR, a status other than "captured", or a negative amount is reported with the reason; a negative ledger amount likewise. The spec says none of these occur, so the tool says so loudly instead of reconciling them as if they were normal. This needed one extra field on `Transaction` (`problem`), because normalisation otherwise discards currency and status. The side effect is that the other side of such a transaction shows up as missing; the report's note says so. A zero amount is not flagged. See questions 6 and 13.

### 6. State: one JSON file, recompute and compare

Each run recomputes all findings and compares them with the stored ones: new ones are reported, stored open ones that no longer apply are marked resolved, the rest are left alone. Open findings keep their rows and are fed back into the next run, which is how a day-1 gap can resolve on day 2. Resolved findings stay in the file with a status; only open ones are carried forward. A resolved finding that returns is reported as new again.

*Rejected: SQLite.* A single file is enough for this volume and needs no connection or table handling. The file is written to a temporary name and renamed, once, at the end of a run, so a failed run leaves nothing half-written.

### 7. Re-run safety: a checksum per processed date

A processed date with identical files is skipped. With changed files it is refused. The guard is not only an optimisation: I checked that without it, re-running an older date reopens an item that a later day had already resolved, because that day's files still show it as missing.

*Considered: remembering only the date* (a corrected export would be silently ignored), *file modification time* (changes on copy), *a last-processed-date marker* (blocks legitimate re-runs and skipped days).

### 8. The report is a CSV file, one per run date

Finance works in spreadsheets, so a CSV can be filtered, sorted and annotated, and nobody has to read the console. Rows are grouped by issue and ordered by time. Amounts are plain numbers so Excel can add them. Times are Amsterdam time with seconds, because rows a few seconds apart need telling apart.

*Rejected: console output* (finance does not run the tool), *a text file* (cannot be filtered), *sorting by amount* (not asked for).

### 9. Time zones

Matching does not use time. The ledger's local time is converted to UTC as the spec describes, and the report shows Amsterdam time because that is what finance and the ledger use.

## Known limits

- **A later file that repeats an earlier row.** If a transaction reappears on one side only in a later day's file, even though it was paired earlier, it is reported as missing on the other side. Rows that matched are not kept. See question 2.
- **Nothing closes a finding except the data changing.** A person dealing with an item in the source system is invisible to the tool, so amount differences, repeated IDs and rows without an ID stay open. Only the first day they appear is reported. See questions 11 and 12.
- **An input row that cannot be read** (missing field, bad date or amount) stops the run with an error. It does not skip or flag the row.
- **A finding that stays open is refreshed quietly.** If its rows change, that is not reported.
- **Dates are assumed to run in order.**
- **The summary counts are only on the console.** A day with nothing new gives a header-only CSV.
- **Not tested yet.** Behaviour across days was checked with small throwaway scenarios, not an automated suite.
