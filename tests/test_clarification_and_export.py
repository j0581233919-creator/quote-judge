"""Tests for QuoteJudge bilingual clarification generator, export formats, and spreadsheet security."""

from __future__ import annotations
import csv
import json
import tempfile
import unittest
from pathlib import Path

from quote_judge.models import (
    Currency,
    Incoterm,
    LineItem,
    Terms,
    Quotation,
    MissingTermAlert,
    MissingTermCategory,
)
from quote_judge.comparator import QuotationComparator
from quote_judge.clarification import (
    ClarificationQuestion,
    ClarificationLetter,
    BilingualClarificationGenerator,
)
from quote_judge.export import (
    QuotationExporter,
    is_potentially_dangerous_formula,
    sanitize_csv_cell,
    desanitize_csv_cell,
    sanitize_csv_row,
    desanitize_csv_row,
)


class TestClarificationAndExport(unittest.TestCase):
    """Verifies bilingual clarification inquiries, CSV formula injection defense, and multi-format exports."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

        # Sample Quote with Missing Terms
        self.incomplete_quote = Quotation(
            quote_id="Q-DEFECT-01",
            supplier_name="Oriental Valve Corporation",
            currency=Currency.USD,
            line_items=[
                LineItem("1", "Gate Valve 6-inch", 10.0, "pcs", 500.0, 5000.0, Currency.USD),
            ],
            total_amount=5000.0,
            terms=Terms(
                # Missing payment terms, delivery lead time, warranty, and Incoterms!
            ),
        )

        # Sample Report
        quote_complete = Quotation(
            quote_id="Q-COMP-02",
            supplier_name="Gulf Valve Ltd",
            currency=Currency.USD,
            line_items=[
                LineItem("1", "Gate Valve 6-inch", 10.0, "pcs", 550.0, 5500.0, Currency.USD),
            ],
            total_amount=5500.0,
            terms=Terms(
                payment_terms="Net 30 days",
                delivery_lead_time_days=14,
                valid_until="2026-12-31",
                incoterm=Incoterm.DAP,
                named_place="Dammam",
                warranty_months=12,
                is_tax_included=False,
                is_shipping_included=True,
                minimum_order_quantity=1.0,
            ),
        )
        comparator = QuotationComparator()
        self.report = comparator.compare([self.incomplete_quote, quote_complete])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_bilingual_clarification_generation(self):
        generator = BilingualClarificationGenerator(
            buyer_company="National Energy Projects Co.",
            contact_person="Director of Procurement",
        )
        letter = generator.generate_letter(self.incomplete_quote)

        self.assertEqual(letter.supplier_name, "Oriental Valve Corporation")
        self.assertEqual(letter.quote_id, "Q-DEFECT-01")
        self.assertTrue(letter.has_critical_items)
        self.assertGreater(len(letter.questions), 3)

        # Check English content
        self.assertIn("Commercial Clarification Request", letter.subject_en)
        self.assertIn("National Energy Projects Co.", letter.body_en)
        self.assertIn("Director of Procurement", letter.body_en)
        self.assertIn("Oriental Valve Corporation", letter.body_en)

        # Check Arabic content
        self.assertIn("السادة / Oriental Valve Corporation المحترمون", letter.body_ar)
        self.assertIn("السلام عليكم ورحمة الله وبركاته", letter.body_ar)
        self.assertIn("National Energy Projects Co.", letter.body_ar)

        # Check markdown rendering
        md_bilingual = letter.to_markdown("bilingual")
        self.assertIn("Commercial Clarification Request", md_bilingual)
        self.assertIn("طلب إيضاحات تجارية", md_bilingual)

        md_en = letter.to_markdown("en")
        self.assertIn("Commercial Clarification Request", md_en)
        self.assertNotIn("طلب إيضاحات تجارية", md_en)

        md_ar = letter.to_markdown("ar")
        self.assertIn("طلب إيضاحات تجارية", md_ar)
        self.assertNotIn("Commercial Clarification Request", md_ar)

    def test_generate_letters_for_report(self):
        generator = BilingualClarificationGenerator()
        letters = generator.generate_letters_for_report(self.report)

        # Only the supplier with missing terms should receive a letter
        self.assertIn("Oriental Valve Corporation", letters)
        self.assertNotIn("Gulf Valve Ltd", letters)

    def test_csv_formula_injection_defense(self):
        # Dangerous formula triggers
        dangerous_inputs = [
            "=SUM(A1:A10)",
            "+123456789@evil.com",
            "-cmd|' /C calc'!A0",
            "@cmd|' /C calc'!A0",
            "\t=1+1",
            "\r=2+2",
        ]
        for val in dangerous_inputs:
            self.assertTrue(is_potentially_dangerous_formula(val))
            sanitized = sanitize_csv_cell(val)
            self.assertTrue(sanitized.startswith("'"))
            # Desanitization roundtrip
            self.assertEqual(desanitize_csv_cell(sanitized), val)

        # Benign numeric inputs must NOT be escaped
        benign_numbers = [-5, +10, -120.50, +0.99, "1500.00", "-50.00", "+25.5"]
        for num in benign_numbers:
            self.assertFalse(is_potentially_dangerous_formula(str(num)))
            sanitized = sanitize_csv_cell(num)
            self.assertFalse(sanitized.startswith("'"))

        # Arabic text and regular strings must NOT be escaped
        benign_strings = ["محبس كروي 4 بوصة", "Gate Valve 6-inch", "SAR", "Net 30 days"]
        for s in benign_strings:
            self.assertFalse(is_potentially_dangerous_formula(s))
            sanitized = sanitize_csv_cell(s)
            self.assertEqual(sanitized, s)

    def test_export_comparison_to_csv(self):
        out_csv = self.dir_path / "comparison.csv"
        p = QuotationExporter.export_comparison_to_csv(self.report, out_csv)
        self.assertTrue(p.exists())

        # Read back and verify CSV headers and rows
        with open(p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertIn("product_description", reader.fieldnames)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["product_description"], "Gate Valve 6-inch")

    def test_export_comparison_to_markdown_and_json(self):
        out_md = self.dir_path / "comparison.md"
        p_md = QuotationExporter.export_comparison_to_markdown(self.report, out_md)
        self.assertTrue(p_md.exists())
        self.assertIn("Supplier Quotation Comparison Report", p_md.read_text(encoding="utf-8"))

        out_json = self.dir_path / "comparison.json"
        p_json = QuotationExporter.export_comparison_to_json(self.report, out_json)
        self.assertTrue(p_json.exists())

        with open(p_json, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
            self.assertEqual(loaded_data["quotes_count"], 2)
            self.assertEqual(len(loaded_data["suppliers"]), 2)

    def test_export_clarification_letters(self):
        generator = BilingualClarificationGenerator()
        letters = generator.generate_letters_for_report(self.report)

        out_dir = self.dir_path / "letters"
        written = QuotationExporter.export_clarification_letters(letters, out_dir, format="md")
        self.assertEqual(len(written), 1)
        self.assertTrue(written[0].exists())
        self.assertIn("clarification_Oriental_Valve_Corporation.md", written[0].name)

    def test_export_overwrite_protection(self):
        out_csv = self.dir_path / "protected.csv"
        out_csv.write_text("existing content", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            QuotationExporter.export_comparison_to_csv(self.report, out_csv, overwrite=False)


if __name__ == "__main__":
    unittest.main()
