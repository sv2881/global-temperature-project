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

## 2026-09-22 - Phase 4: Monthly grid and normalization

### Decisions

- Reindex to one row for every month from January 1880 through December 2025.
- Count missing existing values and completely absent months before filling.
- Fill every gap with pandas time-based linear interpolation.
- Calculate `mu_20` from the 1,200 months in 1901-2000.
- Calculate `mu` and population `sigma` from all 1,752 cleaned months.
- Calculate `d = x - mu_20` and `z = (x - mu) / sigma`.
- Calculate annual anomaly and z-score means from all 12 months of each year.

### Results

- Total months: 1,752
- Absent months added: 65
- Missing values in existing rows: 125
- Months imputed: 190
- `mu_20`: 0.000159 C
- `mu`: 0.046434 C
- Population `sigma`: 0.519783 C
- Total tests passed: 12

### Five warmest years

1. 2024: anomaly 1.167872 C, mean z 2.157510
2. 2023: anomaly 1.153376 C, mean z 2.129622
3. 2025: anomaly 1.012637 C, mean z 1.858857
4. 2016: anomaly 0.981765 C, mean z 1.799464
5. 2022: anomaly 0.960496 C, mean z 1.758544

The final monthly CSV now has the required columns `date`, `anomaly_c`, and
`z`. Chart creation remains separate for Phase 5.

### Next phase

Phase 5 will draw the monthly line with segment colors based on `d`, use a
blue-to-red palette centered at zero, add the reference line and colorbar, and
export the chart at IEEE column width.

## 2026-09-23 - Phase 5: Dual-encoded chart

### Decisions

- Draw one line segment between each pair of monthly observations.
- Color each segment by the average `d` value of its two endpoints.
- Use `RdBu_r`, so negative values are blue and positive values are red.
- Use symmetric color limits with `TwoSlopeNorm` centered at `d = 0`.
- Draw the 1901-2000 mean as a dashed horizontal reference line.
- Add axis labels with units, a title, a legend, and a labeled colorbar.
- Export a vector PDF at the 3.5-inch width of one IEEE column.

### Results

- Monthly observations plotted: 1,752
- Colored line segments: 1,751
- Figure size: 3.5 by 2.7 inches
- Palette: `RdBu_r`
- Color center: `d = 0`
- Output: `outputs/temperature_chart.pdf`

### Next phase

Phase 6 will write the one-page IEEEtran report, add the equations and
booktabs table, include the chart, and compile the final PDF.
