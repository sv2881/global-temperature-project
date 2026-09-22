import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from clean import (
    clean_duplicates_and_outliers,
    complete_monthly_series,
    load_and_parse,
)


class MonthlySeriesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        csv_path = PROJECT_ROOT / "data" / "raw" / "global_temp_dirty_v2.csv"
        parsed, _, _ = load_and_parse(csv_path)
        cleaned, _ = clean_duplicates_and_outliers(parsed)
        cls.monthly, cls.annual, cls.top_five, cls.results = (
            complete_monthly_series(cleaned)
        )

    def test_complete_monthly_grid(self):
        self.assertEqual(len(self.monthly), 1752)
        self.assertEqual(str(self.monthly.iloc[0]["date"].date()), "1880-01-01")
        self.assertEqual(str(self.monthly.iloc[-1]["date"].date()), "2025-12-01")
        self.assertTrue(self.annual["month_count"].eq(12).all())

    def test_interpolation_fills_every_gap(self):
        self.assertEqual(self.results["absent_months_added"], 65)
        self.assertEqual(self.results["missing_in_existing_rows"], 125)
        self.assertEqual(self.results["months_imputed"], 190)
        self.assertFalse(self.monthly["anomaly_c"].isna().any())

    def test_normalization_values(self):
        self.assertEqual(round(self.results["mu20"], 6), 0.000159)
        self.assertEqual(round(self.results["mu"], 6), 0.046434)
        self.assertEqual(round(self.results["sigma"], 6), 0.519783)
        expected_d = self.monthly["anomaly_c"] - self.results["mu20"]
        self.assertLess((self.monthly["d"] - expected_d).abs().max(), 1e-12)
        self.assertAlmostEqual(self.monthly["z"].mean(), 0.0, places=12)
        self.assertAlmostEqual(self.monthly["z"].std(ddof=0), 1.0, places=12)

    def test_five_warmest_years(self):
        self.assertEqual(self.top_five["year"].tolist(), [2024, 2023, 2025, 2016, 2022])
        expected_means = [1.167872, 1.153376, 1.012637, 0.981765, 0.960496]
        actual_means = self.top_five["mean_anomaly_c"].round(6).tolist()
        self.assertEqual(actual_means, expected_means)


if __name__ == "__main__":
    unittest.main()
