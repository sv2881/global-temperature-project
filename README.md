# Global Temperature Cleaning Project

This repository tracks the cleaning and analysis of the simulated monthly
global temperature anomaly data supplied for the assignment.

The work is split into small phases. Each phase gets its own Git commit so the
development history and cleaning decisions are easy to review.

## Phase plan

- [x] Phase 1: Create the project and preserve the raw data
- [x] Phase 2: Parse dates, missing values, and swapped fields
- [x] Phase 3: Sort, remove duplicates, and apply the IQR rule
- [x] Phase 4: Build the monthly grid, interpolate, and calculate statistics
- [ ] Phase 5: Create the dual-encoded temperature chart
- [ ] Phase 6: Write and compile the one-page IEEE report
- [ ] Phase 7: Validate the outputs and prepare the submission ZIP

## Project layout

```text
data/raw/       Original CSV, kept unchanged
docs/           Assignment text and development notes
notebooks/      Walkthrough notebook with saved outputs
outputs/        Cleaned data, logs, chart, and report
src/            Python cleaning code
tests/          Small tests for the parsing rules
```

## Source data

The original file is `data/raw/global_temp_dirty_v2.csv`.

SHA-256:

```text
ea7d5388004b8e2f7fdacc5b13b154bdea12f8cd2e127c53e4dbf22fa0508564
```

The raw file should not be edited. All cleaning will happen in code.

## Development rule

Keep the implementation simple enough to explain line by line. Record each
important cleaning choice in `DEVELOPMENT_LOG.md` and commit one phase at a
time.

## Run the current pipeline

```bash
python3 src/clean.py
python3 -m unittest discover -s tests -v
```

This creates the earlier phase files plus:

- `outputs/cleaned_monthly.csv`
- `outputs/annual_means.csv`
- `outputs/phase4_statistics_log.txt`
