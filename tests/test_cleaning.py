import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from clean import clean_duplicates_and_outliers, load_and_parse


class CleaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        csv_path = PROJECT_ROOT / "data" / "raw" / "global_temp_dirty_v2.csv"
        parsed, _, _ = load_and_parse(csv_path)
        cls.cleaned, cls.results = clean_duplicates_and_outliers(parsed)

    def test_dates_are_sorted_and_unique(self):
        self.assertTrue(self.cleaned["date"].is_monotonic_increasing)
        self.assertFalse(self.cleaned["date"].duplicated().any())
        self.assertEqual(self.results["duplicates_removed"], 20)
        self.assertEqual(len(self.cleaned), 1687)

    def test_iqr_values(self):
        self.assertAlmostEqual(self.results["q1"], -0.385000)
        self.assertAlmostEqual(self.results["q3"], 0.490000)
        self.assertAlmostEqual(self.results["lower_fence"], -1.697500)
        self.assertAlmostEqual(self.results["upper_fence"], 1.802500)

    def test_only_sensor_codes_are_removed(self):
        self.assertEqual(self.results["outliers_removed"], 63)
        self.assertEqual(self.results["sensor_codes_removed"], 63)
        self.assertEqual(self.results["plausible_readings_removed"], 0)
        absolute_values = self.cleaned["anomaly_c"].abs()
        sensor_codes_remain = (
            absolute_values.eq(500.0) | absolute_values.eq(999.0)
        ).any()
        self.assertFalse(sensor_codes_remain)


if __name__ == "__main__":
    unittest.main()
