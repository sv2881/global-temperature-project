import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_TEX = PROJECT_ROOT / "outputs" / "report.tex"
REPORT_PDF = PROJECT_ROOT / "outputs" / "report.pdf"


class ReportTests(unittest.TestCase):
    def test_latex_contains_required_parts(self):
        source = REPORT_TEX.read_text(encoding="utf-8")

        self.assertIn(r"\documentclass[conference]{IEEEtran}", source)
        self.assertEqual(source.count(r"\begin{equation}"), 2)
        self.assertIn(r"\toprule", source)
        self.assertIn(r"\midrule", source)
        self.assertIn(r"\bottomrule", source)
        self.assertIn(
            r"\includegraphics[width=\columnwidth]{temperature_chart.pdf}",
            source,
        )

    def test_compiled_report_is_one_page(self):
        pdf_data = REPORT_PDF.read_bytes()
        self.assertEqual(pdf_data[:5], b"%PDF-")

        result = subprocess.run(
            ["pdfinfo", str(REPORT_PDF)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("Pages:           1", result.stdout)


if __name__ == "__main__":
    unittest.main()
