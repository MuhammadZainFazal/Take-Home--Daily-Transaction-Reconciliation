# Questions to confirm before go-live

Written so each can be sent to the person named and answered on its own. For each: why it matters, and what the tool does until someone answers.

## About the data

### 1. Which day does a row belong to?
**Ask:** the ledger owner.
**Why:** the ledger file for 1 March contains rows booked after midnight UTC (01:00 local on 2 March). The spec says each export covers its own date. What rule does the ledger use, and does the next day's file repeat those rows?
**Until then:** the tool does not use dates to match, so these rows pair up normally. If they are repeated the next day, see question 2.

### 2. Do exports ever repeat rows from earlier days?
**Ask:** the ledger owner and the payment provider.
**Why:** if a transaction shows up again in a later file on only one side, even though it was already paired, it is reported as missing on the other side. Rows that matched are not remembered.
**Until then:** the tool reports it as missing. A person would have to recognise it.

### 3. How long can booking lag behind capture?
**Ask:** the ledger owner and finance.
**Why:** "in the provider, not in the ledger" may just mean "not booked yet". Should a finding wait a number of days before it counts, and should the report show how long it has been open?
**Until then:** every gap is reported on the first day it appears, with a note that it may not be booked yet. Nothing ages or escalates.

### 4. Repeated transaction IDs on one side
**Ask:** the payment provider (provider side) and the ledger owner (ledger side).
**Why:** on day 1 the provider has one ID twice, 4 seconds apart, and the ledger has it once. Is that a double capture, with a customer charged twice, or an export artifact? Can the ledger legitimately hold two entries for one ID?
**Until then:** rows identical in every field are treated as one. Anything else with the same ID is flagged as appearing more than once.

### 5. Which side is right when amounts differ?
**Ask:** finance.
**Why:** the provider shows money moved and the ledger shows the books. Who fixes a difference depends on the answer.
**Until then:** both amounts, the difference and which side is higher are shown. Neither side is declared right.

### 6. Refunds, reversals, other currencies or statuses
**Ask:** the payment provider and finance.
**Why:** none occur in the data (all EUR, all "captured", all amounts positive). What should happen when they do?
**Until then:** such rows are flagged as unexpected values and left out of matching.

### 7. Corrected exports
**Ask:** the payment provider, the ledger owner and finance.
**Why:** if a file for an already-processed date is re-issued with changes, should the tool compare again, refuse, or ask someone?
**Until then:** it refuses and says the files changed.

### 8. Rows without a transaction ID
**Ask:** finance.
**Why:** would finance ever accept a field-based rule (amount, time, merchant) as a match? If so, which, and with what tolerance?
**Until then:** every such row is reported as "No transaction ID" and never matched.

## About the report

### 9. Excel, number format and time zone
**Ask:** finance.
**Why:** a comma-delimited CSV opens in a single column in Dutch-language Excel, which expects a semicolon (and a decimal comma). Also: is English right, are times in Amsterdam time right, and does the amount column need a currency symbol?
**Until then:** comma delimiter, dot decimals, a UTF-8 marker, English text, Amsterdam time with seconds, plain amounts. The delimiter is one constant in `report.py`.

### 10. Is the summary in the right place and shape?
**Ask:** finance.
**Why:** the answer to "does the total match", with the counts, is a short text file next to the CSV and is also printed on the console. Would finance rather see it at the top of the CSV, in an email, or somewhere else?
**Until then:** a separate `summary-DATE.txt`.

### 11. How should a finding be closed by hand?
**Ask:** finance.
**Why:** once an item has been dealt with in the source system, the tool cannot tell. This is the idea behind FIN-124.
**Until then:** items stay open until the data changes, and appear in the report only on the first day.

### 12. Should old open items be listed again?
**Ask:** finance.
**Why:** the report lists only what changed, so an item that stays open disappears from the daily report after day 1. Would a periodic list of everything still open help?
**Until then:** only a count of items still open from earlier days is printed.

### 13. Flagged rows and their other half
**Ask:** finance.
**Why:** a row with an unexpected value is left out of matching, so its counterpart on the other side shows as missing. Is that acceptable, or should the two be shown together?
**Until then:** both appear, and the note on the flagged row says the other side may show as missing.

## About running it

### 14. Skipped or out-of-order days
**Ask:** finance and engineering.
**Why:** what should happen when a day is missed and run later, or run after a later day?
**Until then:** the tool processes whichever date it is given. It is designed for dates in order.

### 15. Bad input
**Ask:** engineering and finance.
**Why:** should a row that cannot be read stop the run, or be skipped and reported? Should a zero amount be flagged?
**Until then:** an unreadable row stops the run with an error. Zero amounts are not flagged.

## About the totals check

### 16. What does "the total for the day" cover?
**Ask:** finance and the ledger owner.
**Why:** the check compares the sums of the two files exported for that date. If the exports are cut differently, or something is booked a day later, the totals can differ without anything being wrong. Do they want the transactions that happened on the day instead?
**Until then:** the sums of the two export files, as exported.

### 17. Must the totals match to the cent?
**Ask:** finance.
**Why:** a tolerance (rounding, a known small difference) would turn some "no" answers into "yes".
**Until then:** exact to the cent.

### 18. What does the manager do with a "no"?
**Ask:** finance.
**Why:** if the difference alone is enough, we are done. If they want to know what explains it, the tool would need to break the difference down.
**Until then:** the difference and the items are shown, but the difference is not broken down.
