# Decisions

What we were likely to face, and what we decided. Anything that needs a real person's answer is in `QUESTIONS.md`.

### Transactions with no ID
**Faced:** Some transactions have no ID on one side or both. Amount, time and merchant can all legitimately differ between the two systems, so any matching rule built on them would be a guess.
**Decided:** Match on the transaction ID only. Anything without an ID goes to a person to review. A wrong match hides a real problem, while an unmatched item only costs a minute.

### The same ID appearing more than once
**Faced:** With repeated IDs we cannot tell which row belongs with which. It could be a double charge, a double booking, or an export artefact.
**Decided:** Rows that are identical in every field are treated as one. Any other repeat is flagged for review.

### Missing on one side and repeated on the other
**Faced:** An ID can be absent on one side while repeated on the other.
**Decided:** Report it as missing first, since that is what finance needs to know. The item still lists every row involved.

### Amounts that differ
**Faced:** Nothing tells us which side is right.
**Decided:** Show both amounts, the difference and which side is higher. Never correct either side.

### Values the data should not contain
**Faced:** The spec says there are no other currencies, no other statuses and no negative amounts. Reconciling such a row as if it were normal would give a misleading result.
**Decided:** Flag it with the reason and leave it out of matching. Its other half may then show as missing, and the report says so.

### Gaps that are only timing
**Faced:** One system may book later than the other, so a gap can close by itself.
**Decided:** Report a gap the first time it appears and keep it open. If the other side turns up later, mark it resolved.

### Remembering between runs
**Faced:** The tool must report only what changed, so it needs memory.
**Decided:** One JSON file. Each run recomputes the findings and compares them with the stored ones. Open items are carried into the next run, and resolved items are kept with a status. A database was not needed for this size.

### Running the same date twice
**Faced:** A repeat run must not duplicate findings or reopen things that were resolved.
**Decided:** A checksum of the input files is stored per date. The same files are skipped, and changed files are refused.

### Time zones
**Faced:** The two systems record time differently.
**Decided:** Convert the ledger time to UTC as the spec says. Matching does not depend on time. The report shows Amsterdam time, with seconds so close-together items can be told apart.

### How finance receives the result
**Faced:** Finance does not read console output, and plain text cannot be filtered or sorted.
**Decided:** One CSV per run date, opened in Excel. Amounts are plain numbers, grouped by issue and then ordered by time.

### Items handled outside the tool
**Faced:** Once someone deals with an item elsewhere, the tool has no way to know.
**Decided:** Items stay open until the data itself changes, and appear in the report only when first raised. A count of what is still open is shown in the summary.

### Whether the day's total matches
**Faced:** Finance needs a yes or no it can repeat to a manager. But matching totals can hide errors that cancel out, and differing totals can be pure timing.
**Decided:** Compare the sums of the two export files, to the cent. State the answer first, with both totals, the difference and which side is higher. Always show how many items need attention next to it, so a "match" is never read as "all clear".

### Input that cannot be read
**Faced:** A row may be malformed.
**Decided:** Stop with an error rather than guess or skip it.
