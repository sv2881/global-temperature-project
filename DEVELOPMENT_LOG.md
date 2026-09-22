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
