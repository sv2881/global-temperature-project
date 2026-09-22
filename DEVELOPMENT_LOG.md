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

## 2026-09-22 - Phase 3: Duplicates and IQR outliers

### Decisions

- Sort by date and original source line so the choice among duplicates is
  repeatable.
- Keep the first record for each month after sorting.
- Calculate quartiles from the deduplicated, non-missing anomaly values.
- Use the assignment rule: keep values between
  `Q1 - 1.5 * IQR` and `Q3 + 1.5 * IQR`.
- Mark outliers before replacing their anomaly values with `NaN`.
- Stop with an error if a sensor code remains or a plausible reading is
  removed.

### Results

- Duplicate rows removed: 20
- Rows after deduplication: 1,687
- Q1: -0.385000 C
- Q3: 0.490000 C
- IQR: 0.875000 C
- Lower fence: -1.697500 C
- Upper fence: 1.802500 C
- Values removed by IQR: 63
- Sensor codes removed: 63
- Sensor codes remaining: 0
- Plausible readings removed: 0
- Total tests passed: 8

The data is sorted and has one record per available month. Missing calendar
months and `NaN` anomaly values are intentionally left for Phase 4.

### Next phase

Phase 4 will reindex the data to every month from January 1880 through
December 2025, interpolate all gaps in time, and calculate the normalization
statistics.
