import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from clean import load_and_parse, parse_anomaly, parse_date, parse_row


class ParsingTests(unittest.TestCase):
    def test_date_formats(self):
        examples = {
            "188001": "1880-01-01",
            "1880/03": "1880-03-01",
            "1880.04": "1880-04-01",
            "1880-05-01": "1880-05-01",
            "11/1880": "1880-11-01",
            "Jun 1880": "1880-06-01",
            "Jan-1990": "1990-01-01",
            "1908 Sep": "1908-09-01",
            "Jan-43": "1943-01-01",
            "7/1/07": "2007-07-01",
        }

        for raw_date, expected in examples.items():
            with self.subTest(raw_date=raw_date):
                self.assertEqual(str(parse_date(raw_date).date()), expected)

    def test_two_digit_year_rule(self):
        self.assertEqual(str(parse_date("Jan-26").date()), "1926-01-01")
        self.assertEqual(str(parse_date("Dec-99").date()), "1999-12-01")
        self.assertEqual(str(parse_date("Jan-00").date()), "2000-01-01")
        self.assertEqual(str(parse_date("Dec-25").date()), "2025-12-01")

    def test_anomaly_formats(self):
        self.assertAlmostEqual(parse_anomaly("-0,199"), -0.199)
        self.assertAlmostEqual(parse_anomaly("0.253\u00b0C"), 0.253)
        self.assertTrue(math.isnan(parse_anomaly("N/A")))

    def test_swapped_row(self):
        date, anomaly, was_swapped = parse_row("-0.066", "Jan-43")
        self.assertEqual(str(date.date()), "1943-01-01")
        self.assertAlmostEqual(anomaly, -0.066)
        self.assertTrue(was_swapped)

    def test_full_file_parses_without_silent_drops(self):
        csv_path = PROJECT_ROOT / "data" / "raw" / "global_temp_dirty_v2.csv"
        data, counts, unparsed_rows = load_and_parse(csv_path)

        self.assertEqual(len(data), 1707)
        self.assertEqual(counts["non_data_lines"], 4)
        self.assertEqual(counts["swapped_rows"], 32)
        self.assertEqual(unparsed_rows, [])


if __name__ == "__main__":
    unittest.main()
