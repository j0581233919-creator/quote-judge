"""Tests for QuoteJudge Command Line Interface (CLI) and Packaging (QJ-005)."""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quote_judge.cli import (
    build_parser,
    cmd_clarify,
    cmd_compare,
    cmd_demo,
    cmd_validate,
    main,
    parse_exchange_rates_arg,
)
from quote_judge.parser import OCRRequiredError


class TestPackagingAndCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create sample valid quotation
        self.valid_quote_path = self.test_dir / "valid_quote.txt"
        self.valid_quote_text = (
            "Supplier: Gulf Industrial Tools\n"
            "Quote ID: Q-2026-VAL\n"
            "Date: 2026-11-01\n"
            "Valid Until: 2026-12-01\n"
            "Currency: SAR\n"
            "Payment Terms: 30 days net\n"
            "Delivery Schedule: 14 days\n"
            "Delivery Terms: DAP Riyadh\n"
            "Warranty: 12 months\n"
            "VAT (15%): Included\n"
            "Shipping: Included\n"
            "MOQ: 1 unit\n\n"
            "LINE ITEMS:\n"
            "Item 1: Digital Caliper 150mm - Qty: 10 pcs - Unit Price: 150.00 - Total: 1500.00\n"
            "Item 2: Micrometer 0-25mm - Qty: 5 pcs - Unit Price: 200.00 - Total: 1000.00\n\n"
            "Subtotal: 2,500.00 SAR\n"
            "Grand Total: 2,500.00 SAR\n"
        )
        self.valid_quote_path.write_text(self.valid_quote_text, encoding="utf-8")

        # Create sample quotation with missing terms
        self.incomplete_quote_path = self.test_dir / "incomplete_quote.md"
        self.incomplete_quote_text = (
            "# Quotation Ref: Q-2026-INC\n"
            "Supplier: Delta Trading\n"
            "Currency: USD\n\n"
            "| Item | Description | Qty | Unit Price | Total |\n"
            "|---|---|---|---|---|\n"
            "| 1 | Digital Caliper 150mm | 10 | 40.00 | 400.00 |\n\n"
            "Total: 400.00 USD\n"
        )
        self.incomplete_quote_path.write_text(self.incomplete_quote_text, encoding="utf-8")

        # Create quotation with arithmetic error
        self.arithmetic_err_path = self.test_dir / "arithmetic_err.txt"
        self.arithmetic_err_text = (
            "Quotation Ref: Q-ERR-01\n"
            "Supplier: Bad Math Co\n"
            "Currency: SAR\n\n"
            "1. Digital Caliper 150mm | Qty: 10 | Unit Price: 100.00 SAR | Total: 1000.00 SAR\n\n"
            "Total: 9999.00 SAR\n"
        )
        self.arithmetic_err_path.write_text(self.arithmetic_err_text, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------
    # 1. Exchange Rate Parsing Tests
    # -------------------------------------------------------------
    def test_parse_exchange_rates_arg_empty(self):
        self.assertEqual(parse_exchange_rates_arg(None), {})
        self.assertEqual(parse_exchange_rates_arg(""), {})
        self.assertEqual(parse_exchange_rates_arg("   "), {})

    def test_parse_exchange_rates_arg_key_value_string(self):
        rates = parse_exchange_rates_arg("USD=3.75,EUR=4.05,aed:1.02")
        self.assertEqual(rates, {"USD": 3.75, "EUR": 4.05, "AED": 1.02})

    def test_parse_exchange_rates_arg_json(self):
        rates = parse_exchange_rates_arg('{"USD": 3.75, "EUR": 4.05}')
        self.assertEqual(rates, {"USD": 3.75, "EUR": 4.05})

    def test_parse_exchange_rates_arg_malformed(self):
        with self.assertRaises(ValueError):
            parse_exchange_rates_arg("USD=not_a_number")
        with self.assertRaises(ValueError):
            parse_exchange_rates_arg("INVALID_ENTRY")
        with self.assertRaises(ValueError):
            parse_exchange_rates_arg("{invalid json}")

    # -------------------------------------------------------------
    # 2. CLI Validate Subcommand Tests
    # -------------------------------------------------------------
    def test_cli_validate_success(self):
        parser = build_parser()
        args = parser.parse_args(["validate", "-f", str(self.valid_quote_path)])
        
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("Quotation Validation Report", output)
        self.assertIn("Gulf Industrial Tools", output)
        self.assertIn("PASS (100% Consistent)", output)
        self.assertIn("PASS (100% Grounded)", output)

    def test_cli_validate_json_mode(self):
        parser = build_parser()
        args = parser.parse_args(["validate", "-f", str(self.valid_quote_path), "--json"])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["supplier_name"], "Gulf Industrial Tools")
        self.assertEqual(data["currency"], "SAR")
        self.assertTrue(data["validation"]["is_valid"])

    def test_cli_validate_with_missing_terms(self):
        parser = build_parser()
        args = parser.parse_args(["validate", "-f", str(self.incomplete_quote_path)])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("Detected", output)
        self.assertIn("omitted or ambiguous condition", output)

    def test_cli_validate_arithmetic_error(self):
        parser = build_parser()
        args = parser.parse_args(["validate", "-f", str(self.arithmetic_err_path)])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 1)
        self.assertIn("FAIL", output)

    def test_cli_validate_scanned_pdf_refusal(self):
        parser = build_parser()
        fake_pdf = self.test_dir / "scanned_image.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 header without selectable text")

        args = parser.parse_args(["validate", "-f", str(fake_pdf)])

        with patch("quote_judge.parser.DocumentLoader.load_file") as mock_loader:
            mock_loader.side_effect = OCRRequiredError(fake_pdf, "No selectable text detected")
            with patch("sys.stderr", new=io.StringIO()) as fake_err:
                code = args.func(args)
                err_output = fake_err.getvalue()

        self.assertEqual(code, 2)
        self.assertIn("Fail-Closed OCR Guardrail", err_output)

    def test_cli_validate_file_not_found(self):
        parser = build_parser()
        missing_file = self.test_dir / "non_existent.txt"
        args = parser.parse_args(["validate", "-f", str(missing_file)])

        with patch("sys.stderr", new=io.StringIO()) as fake_err:
            code = args.func(args)
            err_output = fake_err.getvalue()

        self.assertEqual(code, 1)
        self.assertIn("Error validating quotation", err_output)

    # -------------------------------------------------------------
    # 3. CLI Compare Subcommand Tests
    # -------------------------------------------------------------
    def test_cli_compare_basic(self):
        parser = build_parser()
        args = parser.parse_args([
            "compare",
            "-f", str(self.valid_quote_path), str(self.incomplete_quote_path),
            "--rates", "USD=3.75,SAR=1.0",
        ])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("Supplier Quotation Comparison Report", output)
        self.assertIn("Gulf Industrial Tools", output)
        self.assertIn("Delta Trading", output)

    def test_cli_compare_exports_markdown_csv_json(self):
        parser = build_parser()
        out_md = self.test_dir / "comparison.md"
        out_csv = self.test_dir / "comparison.csv"
        out_json = self.test_dir / "comparison.json"

        args = parser.parse_args([
            "compare",
            "-f", str(self.valid_quote_path), str(self.incomplete_quote_path),
            "--rates", "USD=3.75,SAR=1.0",
            "-o", str(out_md),
            "--csv", str(out_csv),
            "--json", str(out_json),
        ])

        with patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            code = args.func(args)

        self.assertEqual(code, 0)
        self.assertTrue(out_md.exists())
        self.assertTrue(out_csv.exists())
        self.assertTrue(out_json.exists())

        md_content = out_md.read_text(encoding="utf-8")
        self.assertIn("Supplier Quotation Comparison Report", md_content)

        csv_content = out_csv.read_text(encoding="utf-8")
        self.assertIn("product_description", csv_content)

        json_data = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(len(json_data["ranked_suppliers"]), 2)

    def test_cli_compare_invalid_rates(self):
        parser = build_parser()
        args = parser.parse_args([
            "compare",
            "-f", str(self.valid_quote_path),
            "--rates", "BAD_RATES_STR",
        ])

        with patch("sys.stderr", new=io.StringIO()) as fake_err:
            code = args.func(args)
            err_output = fake_err.getvalue()

        self.assertEqual(code, 1)
        self.assertIn("Error parsing --rates", err_output)

    # -------------------------------------------------------------
    # 4. CLI Clarify Subcommand Tests
    # -------------------------------------------------------------
    def test_cli_clarify_generates_letters(self):
        parser = build_parser()
        letters_dir = self.test_dir / "clarification_letters"
        args = parser.parse_args([
            "clarify",
            "-f", str(self.incomplete_quote_path),
            "-o", str(letters_dir),
            "--buyer-company", "Apex Construction LLC",
            "--contact-person", "Procurement Officer",
        ])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("Successfully generated", output)
        self.assertTrue(letters_dir.exists())
        files = list(letters_dir.glob("*.md"))
        self.assertEqual(len(files), 1)
        content = files[0].read_text(encoding="utf-8")
        self.assertIn("Apex Construction LLC", content)
        self.assertIn("Procurement Officer", content)

    def test_cli_clarify_json_format(self):
        parser = build_parser()
        letters_dir = self.test_dir / "json_letters"
        args = parser.parse_args([
            "clarify",
            "-f", str(self.incomplete_quote_path),
            "-o", str(letters_dir),
            "--format", "json",
        ])

        with patch("sys.stdout", new=io.StringIO()):
            code = args.func(args)

        self.assertEqual(code, 0)
        json_files = list(letters_dir.glob("*.json"))
        self.assertEqual(len(json_files), 1)
        data = json.loads(json_files[0].read_text(encoding="utf-8"))
        self.assertEqual(data["supplier_name"], "Delta Trading")
        self.assertTrue(len(data["questions"]) > 0)

    # -------------------------------------------------------------
    # 5. CLI Demo Subcommand Tests
    # -------------------------------------------------------------
    def test_cli_demo(self):
        parser = build_parser()
        args = parser.parse_args(["demo"])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("QuoteJudge — Multi-Supplier Comparative Quotation Engine", output)
        self.assertIn("Gulf Valve & Pipeline FZE", output)
        self.assertIn("Demo completed successfully", output)

    # -------------------------------------------------------------
    # 6. Parser and Entry Point Tests
    # -------------------------------------------------------------
    def test_main_without_subcommand(self):
        with patch.object(sys, "argv", ["quote-judge"]), patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = main()
            output = fake_out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("usage: quote-judge", output)

    def test_main_help_flag(self):
        with patch.object(sys, "argv", ["quote-judge", "--help"]), patch("sys.stdout", new=io.StringIO()) as fake_out:
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
