# Development Log

## 2026-09-22 - Phase 1: Project setup

### What was added

- A fresh project folder and Git repository
- The original CSV in `data/raw/`
- The assignment text in `docs/`
- Empty folders for code, notebook work, and outputs
- A short phase checklist and pinned Python requirements

### Data provenance

- Original filename: `global_temp_dirty_v2.csv`
- File length: 1,712 lines including the header and trailing non-data lines
- SHA-256: `ea7d5388004b8e2f7fdacc5b13b154bdea12f8cd2e127c53e4dbf22fa0508564`

The copied CSV has the same checksum as the supplied file. No cleaning or
manual edits have been made yet.

### Next phase

Phase 2 will read every field as text and implement the date, anomaly, missing
value, and swapped-field parsing rules. Unparsed rows will be reported instead
of silently removed.

## 2026-09-22 - Phase 2: Parse the dirty fields

### Decisions

- Read the CSV with Python's `csv` module so every input starts as text.
- Strip the header names before finding the date and anomaly columns.
- Parse each date format explicitly instead of relying on automatic guessing.
- Interpret two-digit years 26-99 as 19xx and 00-25 as 20xx.
- Set every parsed date to the first day of its month.
- Treat every listed missing-value token as `NaN`.
- Replace comma decimals with decimal points and remove the degree-C suffix.
- Try the normal column order first. If it fails, try the two fields swapped.
- Keep the original CSV line number and mark every repaired swap.
- Write any row that still fails into the parsing log.

### Results

- CSV records after the header: 1,711
- Non-data lines discarded: 4
- Data rows parsed: 1,707
- Swapped rows repaired: 32
- Unparsed data rows: 0
- Date dtype in memory: `datetime64[ns]`
- Parsing tests passed: 5

The output still contains duplicates, missing anomalies, sensor codes, and
out-of-order rows. Those belong to later phases and were intentionally left
unchanged here.

### Next phase

Phase 3 will sort the parsed rows, keep one record per month, calculate the IQR
fences, and replace IQR outliers with `NaN`.
