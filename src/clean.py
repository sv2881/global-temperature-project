#!/usr/bin/env python3
"""Parse and clean the simulated global temperature data."""

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


def clean_duplicates_and_outliers(data):
    """Sort, keep one row per month, and apply the IQR rule."""
    cleaned = data.sort_values(["date", "source_line"], kind="mergesort").copy()

    duplicates_removed = int(cleaned.duplicated("date").sum())
    cleaned = cleaned.drop_duplicates("date", keep="first").copy()

    values = cleaned["anomaly_c"]
    non_missing = values.dropna()

    q1 = float(non_missing.quantile(0.25))
    q3 = float(non_missing.quantile(0.75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    outlier_mask = values.notna() & (
        (values < lower_fence) | (values > upper_fence)
    )
    absolute_values = values.abs()
    sensor_mask = absolute_values.eq(500.0) | absolute_values.eq(999.0)

    sensor_codes_removed = int((outlier_mask & sensor_mask).sum())
    plausible_readings_removed = int((outlier_mask & ~sensor_mask).sum())

    cleaned["was_outlier"] = outlier_mask
    cleaned.loc[outlier_mask, "anomaly_c"] = np.nan
    cleaned = cleaned.reset_index(drop=True)

    remaining_values = cleaned["anomaly_c"].abs()
    sensor_codes_remaining = int(
        (remaining_values.eq(500.0) | remaining_values.eq(999.0)).sum()
    )
    if sensor_codes_remaining != 0:
        raise ValueError("A sensor code remained after applying the IQR rule.")
    if plausible_readings_removed != 0:
        raise ValueError("The IQR rule removed a plausible temperature reading.")

    results = {
        "duplicates_removed": duplicates_removed,
        "rows_after_deduplication": len(cleaned),
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "outliers_removed": int(outlier_mask.sum()),
        "sensor_codes_removed": sensor_codes_removed,
        "sensor_codes_remaining": sensor_codes_remaining,
        "plausible_readings_removed": plausible_readings_removed,
    }

    return cleaned, results


def write_phase2_outputs(data, counts, unparsed_rows, output_dir):
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


def write_phase3_outputs(data, results, output_dir):
    csv_output = data.copy()
    csv_output["date"] = csv_output["date"].dt.strftime("%Y-%m-%d")
    csv_output.to_csv(output_dir / "phase3_cleaned.csv", index=False)

    log_lines = [
        "PHASE 3 CLEANING LOG",
        "",
        f"Duplicate rows removed: {results['duplicates_removed']}",
        f"Rows after deduplication: {results['rows_after_deduplication']}",
        f"Q1: {results['q1']:.6f} C",
        f"Q3: {results['q3']:.6f} C",
        f"IQR: {results['iqr']:.6f} C",
        f"Lower fence: {results['lower_fence']:.6f} C",
        f"Upper fence: {results['upper_fence']:.6f} C",
        f"Values removed by IQR: {results['outliers_removed']}",
        f"Sensor codes removed: {results['sensor_codes_removed']}",
        f"Sensor codes remaining: {results['sensor_codes_remaining']}",
        f"Plausible readings removed: {results['plausible_readings_removed']}",
    ]

    (output_dir / "phase3_cleaning_log.txt").write_text(
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

    write_phase2_outputs(data, counts, unparsed_rows, args.output_dir)
    cleaned, cleaning_results = clean_duplicates_and_outliers(data)
    write_phase3_outputs(cleaned, cleaning_results, args.output_dir)

    print(f"Parsed rows: {counts['parsed_rows']}")
    print(f"Repaired swaps: {counts['swapped_rows']}")
    print(f"Unparsed rows: {counts['unparsed_rows']}")
    print(f"Date dtype: {data['date'].dtype}")
    print(f"Duplicates removed: {cleaning_results['duplicates_removed']}")
    print(
        "IQR fences: "
        f"[{cleaning_results['lower_fence']:.6f}, "
        f"{cleaning_results['upper_fence']:.6f}]"
    )
    print(f"Outliers removed: {cleaning_results['outliers_removed']}")
    print(
        "Plausible readings removed: "
        f"{cleaning_results['plausible_readings_removed']}"
    )


if __name__ == "__main__":
    main()
