"""Tests for QuoteJudge document parser and multi-format loader."""

from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from quote_judge.parser import (
    DocumentLoader,
    LoadedDocument,
    OCRRequiredError,
    UnsupportedFormatError,
)


class TestDocumentLoader(unittest.TestCase):
    """Verifies file ingestion across supported document formats and fail-closed error handling."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_text_file(self):
        txt_path = self.dir_path / "quote.txt"
        txt_content = "Supplier: Alpha Trading Co.\nQuote ID: AT-101\nTotal: 1000.00 USD"
        txt_path.write_text(txt_content, encoding="utf-8")

        doc = DocumentLoader.load_file(txt_path)
        self.assertEqual(doc.file_format, "txt")
        self.assertEqual(doc.raw_text, txt_content)
        self.assertEqual(doc.line_count, 3)
        self.assertEqual(doc.char_count, len(txt_content))
        self.assertEqual(doc.document_id, "quote.txt")

    def test_load_markdown_file(self):
        md_path = self.dir_path / "quote.md"
        md_content = "# Quotation\n| Item | Qty | Price |\n| --- | --- | --- |\n| Bolt | 100 | 5.00 |"
        md_path.write_text(md_content, encoding="utf-8")

        doc = DocumentLoader.load_file(md_path)
        self.assertEqual(doc.file_format, "md")
        self.assertIn("Bolt", doc.raw_text)
        self.assertEqual(doc.document_id, "quote.md")

    def test_load_csv_file(self):
        csv_path = self.dir_path / "items.csv"
        csv_content = "item,qty,unit_price,total\nSteel Bar,50,20.00,1000.00\nCopper Rod,10,50.00,500.00"
        csv_path.write_text(csv_content, encoding="utf-8")

        doc = DocumentLoader.load_file(csv_path)
        self.assertEqual(doc.file_format, "csv")
        self.assertEqual(doc.metadata.get("csv_rows"), 3)

    def test_load_json_file(self):
        json_path = self.dir_path / "quote.json"
        json_content = '{"quote_id": "J-99", "supplier": "Json Supplies Ltd", "total": 5000}'
        json_path.write_text(json_content, encoding="utf-8")

        doc = DocumentLoader.load_file(json_path)
        self.assertEqual(doc.file_format, "json")
        self.assertIn("quote_id", doc.metadata.get("json_keys", []))

    def test_load_unsupported_format_raises_error(self):
        doc_path = self.dir_path / "quote.docx"
        doc_path.write_text("Dummy binary content", encoding="utf-8")

        with self.assertRaises(UnsupportedFormatError):
            DocumentLoader.load_file(doc_path)

    def test_load_non_existent_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            DocumentLoader.load_file(self.dir_path / "does_not_exist.txt")

    def test_load_text_memory(self):
        inline_text = "Quotation Body Text"
        doc = DocumentLoader.load_text(inline_text, document_id="mem_doc_1")
        self.assertEqual(doc.document_id, "mem_doc_1")
        self.assertEqual(doc.raw_text, inline_text)
        self.assertIsNone(doc.file_path)

    @patch("subprocess.run")
    def test_pdf_extraction_scanned_image_raises_ocr_required(self, mock_run):
        # Mock pdftotext returning empty output (typical of scanned PDF)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   \n\n   \f"  # Whitespace only
        mock_run.return_value = mock_result

        pdf_path = self.dir_path / "scanned_quote.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 dummy binary content")

        with self.assertRaises(OCRRequiredError) as ctx:
            DocumentLoader.load_file(pdf_path)
        self.assertIn("contains no extractable text stream", str(ctx.exception))
        self.assertIn("strictly operates on verifiable text", str(ctx.exception))

    @patch("subprocess.run")
    def test_pdf_extraction_text_based_pdf_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Supplier: Emirates Global Pipe FZE\nQuote ID: EGP-5001\nTotal: 25000.00 AED"
        mock_run.return_value = mock_result

        pdf_path = self.dir_path / "digital_quote.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 dummy pdf bytes")

        doc = DocumentLoader.load_file(pdf_path)
        self.assertEqual(doc.file_format, "pdf")
        self.assertIn("Emirates Global Pipe FZE", doc.raw_text)
        self.assertEqual(doc.metadata.get("extractor"), "pdftotext")

    def test_real_system_pdf_extraction_with_pdftotext(self):
        """End-to-end integration test generating a genuine text PDF with ps2pdf and extracting it via pdftotext."""
        import subprocess, shutil
        if not shutil.which("ps2pdf") or not shutil.which("pdftotext"):
            self.skipTest("ps2pdf or pdftotext not installed in environment")

        ps_content = (
            "%!PS\n"
            "/Helvetica findfont 12 scalefont setfont\n"
            "100 700 moveto (Supplier: Gulf Energy Equipment FZE) show\n"
            "100 680 moveto (Quote ID: GEE-2026-NOV-412) show\n"
            "100 660 moveto (Grand Total: 47725.00 SAR) show\n"
            "showpage\n"
        )
        ps_path = self.dir_path / "sample.ps"
        pdf_path = self.dir_path / "sample.pdf"
        ps_path.write_text(ps_content, encoding="ascii")

        subprocess.run(["ps2pdf", str(ps_path), str(pdf_path)], check=True)

        doc = DocumentLoader.load_file(pdf_path)
        self.assertEqual(doc.file_format, "pdf")
        self.assertIn("Gulf Energy Equipment FZE", doc.raw_text)
        self.assertIn("GEE-2026-NOV-412", doc.raw_text)
        self.assertIn("47725.00 SAR", doc.raw_text)


if __name__ == "__main__":
    unittest.main()
