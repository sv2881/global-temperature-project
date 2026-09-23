#!/usr/bin/env python3
"""Parse and clean the simulated global temperature data."""

__author__ = "Siva Srinivas Venigalla"
__email__ = "sv2881@nyu.edu"

import argparse
import csv
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.colors import TwoSlopeNorm


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

START_MONTH = pd.Timestamp("1880-01-01")
END_MONTH = pd.Timestamp("2025-12-01")

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


def complete_monthly_series(data):
    """Create the full grid, interpolate gaps, and calculate statistics."""
    full_index = pd.date_range(START_MONTH, END_MONTH, freq="MS")
    values = data.set_index("date")[["anomaly_c"]]

    absent_months = len(full_index.difference(values.index))
    missing_in_existing_rows = int(values["anomaly_c"].isna().sum())

    monthly = values.reindex(full_index)
    monthly.index.name = "date"
    monthly["was_imputed"] = monthly["anomaly_c"].isna()
    months_imputed = int(monthly["was_imputed"].sum())

    monthly["anomaly_c"] = monthly["anomaly_c"].interpolate(method="time")
    if monthly["anomaly_c"].isna().any():
        raise ValueError("Interpolation left missing monthly values.")

    baseline = monthly.loc["1901-01-01":"2000-12-01", "anomaly_c"]
    mu20 = float(baseline.mean())
    mu = float(monthly["anomaly_c"].mean())
    sigma = float(monthly["anomaly_c"].std(ddof=0))

    monthly["d"] = monthly["anomaly_c"] - mu20
    monthly["z"] = (monthly["anomaly_c"] - mu) / sigma
    monthly = monthly.reset_index()

    annual = monthly.copy()
    annual["year"] = annual["date"].dt.year
    annual = annual.groupby("year", as_index=False).agg(
        mean_anomaly_c=("anomaly_c", "mean"),
        mean_z=("z", "mean"),
        month_count=("date", "size"),
    )

    if len(monthly) != 1752 or not annual["month_count"].eq(12).all():
        raise ValueError("The monthly grid is incomplete.")

    top_five = annual.nlargest(5, "mean_anomaly_c").reset_index(drop=True)

    results = {
        "total_months": len(monthly),
        "absent_months_added": absent_months,
        "missing_in_existing_rows": missing_in_existing_rows,
        "months_imputed": months_imputed,
        "mu20": mu20,
        "mu": mu,
        "sigma": sigma,
    }

    return monthly, annual, top_five, results


def build_temperature_chart(monthly, mu20):
    """Build the dual-encoded monthly temperature chart."""
    dates = mdates.date2num(monthly["date"])
    temperatures = monthly["anomaly_c"].to_numpy()
    differences = monthly["d"].to_numpy()

    points = np.column_stack([dates, temperatures])
    segments = np.stack([points[:-1], points[1:]], axis=1)
    segment_differences = (differences[:-1] + differences[1:]) / 2

    color_limit = float(np.abs(differences).max())
    color_norm = TwoSlopeNorm(
        vmin=-color_limit,
        vcenter=0,
        vmax=color_limit,
    )

    fig, ax = plt.subplots(figsize=(3.5, 2.7), layout="constrained")
    colored_line = LineCollection(
        segments,
        cmap="RdBu_r",
        norm=color_norm,
        linewidth=0.8,
    )
    colored_line.set_array(segment_differences)
    ax.add_collection(colored_line)

    ax.set_xlim(dates.min(), dates.max())
    y_padding = 0.08 * (temperatures.max() - temperatures.min())
    ax.set_ylim(temperatures.min() - y_padding, temperatures.max() + y_padding)
    ax.axhline(
        mu20,
        color="black",
        linestyle="--",
        linewidth=0.7,
        label="1901-2000 mean",
    )

    ax.set_title("Global Temperature Anomaly, 1880-2025", fontsize=8.5)
    ax.set_xlabel("Year", fontsize=7.5)
    ax.set_ylabel(r"Temperature anomaly ($^\circ$C)", fontsize=7.5)
    ax.xaxis.set_major_locator(mdates.YearLocator(30))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(labelsize=6.5)
    ax.grid(axis="y", color="0.85", linewidth=0.5)
    ax.legend(loc="upper left", frameon=False, fontsize=6.5)

    colorbar = fig.colorbar(
        colored_line,
        ax=ax,
        orientation="horizontal",
        pad=0.10,
        fraction=0.11,
        aspect=28,
    )
    colorbar.set_label(
        r"Difference from 1901-2000 mean, $d$ ($^\circ$C)",
        fontsize=7,
    )
    colorbar.ax.tick_params(labelsize=6.5)

    return fig, ax, colored_line


def write_temperature_chart(monthly, mu20, output_path):
    """Write the chart as a vector PDF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, _, _ = build_temperature_chart(monthly, mu20)
    fig.savefig(
        output_path,
        format="pdf",
        metadata={
            "Title": "Global Temperature Anomaly, 1880-2025",
            "Creator": "Matplotlib",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)


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


def write_phase4_outputs(monthly, annual, top_five, results, output_dir):
    monthly_output = monthly.copy()
    monthly_output["date"] = monthly_output["date"].dt.strftime("%Y-%m")
    monthly_output.to_csv(
        output_dir / "cleaned_monthly.csv",
        index=False,
        columns=["date", "anomaly_c", "z"],
        float_format="%.6f",
    )

    annual.to_csv(
        output_dir / "annual_means.csv",
        index=False,
        columns=["year", "mean_anomaly_c", "mean_z"],
        float_format="%.6f",
    )

    log_lines = [
        "PHASE 4 MONTHLY GRID AND STATISTICS",
        "",
        f"Total months: {results['total_months']}",
        f"Absent months added: {results['absent_months_added']}",
        f"Missing values in existing rows: {results['missing_in_existing_rows']}",
        f"Months imputed: {results['months_imputed']}",
        "Interpolation method: linear in time",
        "",
        f"mu_20 (1901-2000): {results['mu20']:.6f} C",
        f"mu (1880-2025): {results['mu']:.6f} C",
        f"sigma (population): {results['sigma']:.6f} C",
        "",
        "FIVE WARMEST YEARS",
    ]

    for rank, row in enumerate(top_five.itertuples(index=False), start=1):
        log_lines.append(
            f"{rank}. {row.year}: mean anomaly {row.mean_anomaly_c:.6f} C, "
            f"mean z {row.mean_z:.6f}"
        )

    (output_dir / "phase4_statistics_log.txt").write_text(
        "\n".join(log_lines) + "\n", encoding="utf-8"
    )


def write_cleaning_log(
    counts,
    unparsed_rows,
    cleaning_results,
    statistics,
    output_dir,
):
    """Write one final log containing the required cleaning counts."""
    log_lines = [
        "GLOBAL TEMPERATURE CLEANING LOG",
        "",
        "PARSING",
        f"CSV records after header: {counts['source_records']}",
        f"Non-data lines discarded: {counts['non_data_lines']}",
        f"Data rows parsed: {counts['parsed_rows']}",
        f"Swapped rows repaired: {counts['swapped_rows']}",
        f"Unparsed data rows: {counts['unparsed_rows']}",
        "",
        "DUPLICATES AND IQR OUTLIERS",
        f"Duplicate rows removed: {cleaning_results['duplicates_removed']}",
        f"Rows after deduplication: {cleaning_results['rows_after_deduplication']}",
        f"Q1: {cleaning_results['q1']:.6f} C",
        f"Q3: {cleaning_results['q3']:.6f} C",
        f"IQR: {cleaning_results['iqr']:.6f} C",
        f"Lower fence: {cleaning_results['lower_fence']:.6f} C",
        f"Upper fence: {cleaning_results['upper_fence']:.6f} C",
        f"Values removed by IQR: {cleaning_results['outliers_removed']}",
        f"Sensor codes removed: {cleaning_results['sensor_codes_removed']}",
        f"Sensor codes remaining: {cleaning_results['sensor_codes_remaining']}",
        "Plausible readings removed: "
        f"{cleaning_results['plausible_readings_removed']}",
        "",
        "MONTHLY GRID AND INTERPOLATION",
        f"Total months: {statistics['total_months']}",
        f"Absent months added: {statistics['absent_months_added']}",
        "Missing values in existing rows: "
        f"{statistics['missing_in_existing_rows']}",
        f"Months imputed: {statistics['months_imputed']}",
        "Interpolation method: linear in time",
        "",
        "UNPARSED ROWS",
    ]

    if unparsed_rows:
        log_lines.extend(unparsed_rows)
    else:
        log_lines.append("None")

    log_path = output_dir / "cleaning_log.txt"
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return log_path


def main():
    script_dir = Path(__file__).resolve().parent
    if script_dir.name == "src":
        project_root = script_dir.parent
        default_input = project_root / "data" / "raw" / "global_temp_dirty_v2.csv"
        default_output = project_root / "outputs"
    else:
        default_input = script_dir / "global_temp_dirty_v2.csv"
        default_output = script_dir

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_csv",
        nargs="?",
        type=Path,
        default=default_input,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output,
    )
    args = parser.parse_args()

    data, counts, unparsed_rows = load_and_parse(args.input_csv)

    if not pd.api.types.is_datetime64_any_dtype(data["date"]):
        raise TypeError("Date parsing did not produce a datetime64 column.")

    write_phase2_outputs(data, counts, unparsed_rows, args.output_dir)
    cleaned, cleaning_results = clean_duplicates_and_outliers(data)
    write_phase3_outputs(cleaned, cleaning_results, args.output_dir)
    monthly, annual, top_five, statistics = complete_monthly_series(cleaned)
    write_phase4_outputs(monthly, annual, top_five, statistics, args.output_dir)
    cleaning_log_path = write_cleaning_log(
        counts,
        unparsed_rows,
        cleaning_results,
        statistics,
        args.output_dir,
    )
    chart_path = args.output_dir / "temperature_chart.pdf"
    write_temperature_chart(monthly, statistics["mu20"], chart_path)

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
    print(f"Months imputed: {statistics['months_imputed']}")
    print(
        f"mu_20={statistics['mu20']:.6f}, "
        f"mu={statistics['mu']:.6f}, "
        f"sigma={statistics['sigma']:.6f}"
    )
    print("Five warmest years:")
    for row in top_five.itertuples(index=False):
        print(
            f"{row.year}: anomaly={row.mean_anomaly_c:.6f}, "
            f"mean_z={row.mean_z:.6f}"
        )
    print(f"Chart: {chart_path}")
    print(f"Cleaning log: {cleaning_log_path}")


if __name__ == "__main__":
    main()
