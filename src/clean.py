#!/usr/bin/env python3
"""Phase 2: parse dates and anomaly values without dropping data rows."""

import argparse
import csv
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


MISSING_VALUES = {
    "",
    ".",
    "--",
    "nan",
    "null",
    "na",
    "n/a",
    "#n/a",
    "missing",
}

MONTH_NUMBERS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def expand_year(text):
    """Convert a two-digit year using the rule given in the assignment."""
    year = int(text)
    if len(text) == 2:
        if year >= 26:
            return 1900 + year
        return 2000 + year
    return year


def make_date(year, month):
    """Return the first day of a valid month in the data range."""
    if 1880 <= year <= 2025 and 1 <= month <= 12:
        return pd.Timestamp(year=year, month=month, day=1)
    return None


def month_number(name):
    return MONTH_NUMBERS.get(name.strip().lower()[:3])


def parse_date(value):
    text = value.strip()
    if text.lower() in MISSING_VALUES:
        return None

    # YYYYMM
    match = re.fullmatch(r"(\d{4})(\d{2})", text)
    if match:
        return make_date(int(match.group(1)), int(match.group(2)))

    # YYYY-MM-DD, YYYY/MM/DD, or YYYY.MM.DD
    match = re.fullmatch(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if match:
        return make_date(int(match.group(1)), int(match.group(2)))

    # M/D/YY or M/D/YYYY. The day is ignored.
    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2}|\d{4})", text)
    if match:
        return make_date(expand_year(match.group(3)), int(match.group(1)))

    # YYYY-MM, YYYY/MM, or YYYY.MM
    match = re.fullmatch(r"(\d{4})[./-](\d{1,2})", text)
    if match:
        return make_date(int(match.group(1)), int(match.group(2)))

    # MM-YYYY, MM/YYYY, or MM-YY
    match = re.fullmatch(r"(\d{1,2})[./-](\d{2}|\d{4})", text)
    if match:
        return make_date(expand_year(match.group(2)), int(match.group(1)))

    # Jan-1990, Jun 1880, or Jan-43
    match = re.fullmatch(r"([A-Za-z]+)[ -]+(\d{2}|\d{4})", text)
    if match:
        month = month_number(match.group(1))
        if month is not None:
            return make_date(expand_year(match.group(2)), month)

    # 1908 Sep or 1881 Dec
    match = re.fullmatch(r"(\d{2}|\d{4})[ -]+([A-Za-z]+)", text)
    if match:
        month = month_number(match.group(2))
        if month is not None:
            return make_date(expand_year(match.group(1)), month)

    return None


def parse_anomaly(value):
    text = value.strip()
    if text.lower() in MISSING_VALUES:
        return np.nan

    text = re.sub(r"\s*\u00b0\s*[Cc]\s*$", "", text)
    text = text.replace(",", ".")
    number = float(text)

    if not math.isfinite(number):
        return np.nan
    return number


def parse_row(raw_date, raw_anomaly):
    """Try the normal field order first, then try the swapped order."""
    date = parse_date(raw_date)
    if date is not None:
        try:
            return date, parse_anomaly(raw_anomaly), False
        except ValueError:
            pass

    date = parse_date(raw_anomaly)
    if date is not None:
        try:
            return date, parse_anomaly(raw_date), True
        except ValueError:
            pass

    return None


def is_non_data_row(row, raw_date):
    if not any(field.strip() for field in row):
        return True
    if raw_date == "END OF DATA":
        return True
    if raw_date.startswith("Source:"):
        return True
    return False


def load_and_parse(csv_path):
    parsed_rows = []
    unparsed_rows = []
    counts = {
        "source_records": 0,
        "non_data_lines": 0,
        "swapped_rows": 0,
    }

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        header = [name.strip() for name in next(reader)]

        date_column = header.index("Date")
        anomaly_column = header.index("Temperature_Anomaly")

        for line_number, row in enumerate(reader, start=2):
            counts["source_records"] += 1
            row = row + [""] * max(0, len(header) - len(row))

            raw_date = row[date_column].strip()
            raw_anomaly = row[anomaly_column].strip()

            if is_non_data_row(row, raw_date):
                counts["non_data_lines"] += 1
                continue

            result = parse_row(raw_date, raw_anomaly)
            if result is None:
                unparsed_rows.append(
                    f"line {line_number}: Date={raw_date!r}, "
                    f"Temperature_Anomaly={raw_anomaly!r}"
                )
                continue

            date, anomaly, was_swapped = result
            if was_swapped:
                counts["swapped_rows"] += 1

            parsed_rows.append(
                {
                    "source_line": line_number,
                    "date": date,
                    "anomaly_c": anomaly,
                    "repaired_swap": was_swapped,
                }
            )

    data = pd.DataFrame(parsed_rows)
    data["date"] = pd.to_datetime(data["date"])
    counts["parsed_rows"] = len(data)
    counts["unparsed_rows"] = len(unparsed_rows)

    return data, counts, unparsed_rows


def write_outputs(data, counts, unparsed_rows, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_output = data.copy()
    csv_output["date"] = csv_output["date"].dt.strftime("%Y-%m-%d")
    csv_output.to_csv(output_dir / "phase2_parsed.csv", index=False)

    log_lines = [
        "PHASE 2 PARSING LOG",
        "",
        f"CSV records after header: {counts['source_records']}",
        f"Non-data lines discarded: {counts['non_data_lines']}",
        f"Data rows parsed: {counts['parsed_rows']}",
        f"Swapped rows repaired: {counts['swapped_rows']}",
        f"Unparsed data rows: {counts['unparsed_rows']}",
        f"Date dtype in memory: {data['date'].dtype}",
        "",
        "UNPARSED ROWS",
    ]

    if unparsed_rows:
        log_lines.extend(unparsed_rows)
    else:
        log_lines.append("None")

    (output_dir / "phase2_parsing_log.txt").write_text(
        "\n".join(log_lines) + "\n", encoding="utf-8"
    )


def main():
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_csv",
        nargs="?",
        type=Path,
        default=project_root / "data" / "raw" / "global_temp_dirty_v2.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "outputs",
    )
    args = parser.parse_args()

    data, counts, unparsed_rows = load_and_parse(args.input_csv)

    if not pd.api.types.is_datetime64_any_dtype(data["date"]):
        raise TypeError("Date parsing did not produce a datetime64 column.")

    write_outputs(data, counts, unparsed_rows, args.output_dir)

    print(f"Parsed rows: {counts['parsed_rows']}")
    print(f"Repaired swaps: {counts['swapped_rows']}")
    print(f"Unparsed rows: {counts['unparsed_rows']}")
    print(f"Date dtype: {data['date'].dtype}")


if __name__ == "__main__":
    main()
