import sys
import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from clean import (
    build_temperature_chart,
    clean_duplicates_and_outliers,
    complete_monthly_series,
    load_and_parse,
    write_temperature_chart,
)


class TemperatureChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        csv_path = PROJECT_ROOT / "data" / "raw" / "global_temp_dirty_v2.csv"
        parsed, _, _ = load_and_parse(csv_path)
        cleaned, _ = clean_duplicates_and_outliers(parsed)
        cls.monthly, _, _, cls.results = complete_monthly_series(cleaned)

    def test_chart_uses_required_size_and_color_encoding(self):
        fig, _, colored_line = build_temperature_chart(
            self.monthly,
            self.results["mu20"],
        )
        try:
            width, height = fig.get_size_inches()
            self.assertEqual(round(width, 1), 3.5)
            self.assertEqual(round(height, 1), 2.7)
            self.assertEqual(len(colored_line.get_segments()), 1751)
            self.assertEqual(colored_line.cmap.name, "RdBu_r")
            self.assertIsInstance(colored_line.norm, TwoSlopeNorm)
            self.assertEqual(colored_line.norm.vcenter, 0)
            self.assertAlmostEqual(
                colored_line.norm.vmin,
                -colored_line.norm.vmax,
            )
        finally:
            plt.close(fig)

    def test_chart_has_labels_colorbar_and_reference_line(self):
        fig, ax, _ = build_temperature_chart(
            self.monthly,
            self.results["mu20"],
        )
        try:
            self.assertEqual(ax.get_xlabel(), "Year")
            self.assertIn("Temperature anomaly", ax.get_ylabel())
            self.assertTrue(ax.get_title())
            self.assertEqual(len(ax.lines), 1)
            self.assertIn("1901-2000 mean", ax.lines[0].get_label())
            self.assertIn("Difference from 1901-2000 mean", fig.axes[1].get_xlabel())
        finally:
            plt.close(fig)

    def test_vector_pdf_is_written(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_path = Path(temporary_dir) / "temperature_chart.pdf"
            write_temperature_chart(
                self.monthly,
                self.results["mu20"],
                output_path,
            )
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 10_000)
            self.assertEqual(output_path.read_bytes()[:5], b"%PDF-")


if __name__ == "__main__":
    unittest.main()
