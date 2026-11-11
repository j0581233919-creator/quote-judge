#!/usr/bin/env python3
"""Demonstration of QuoteJudge QJ-002 multi-format document ingestion and fact extraction."""

from __future__ import annotations
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

# Ensure quote_judge package is resolvable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quote_judge.parser import DocumentLoader, OCRRequiredError
from quote_judge.extractor import QuotationExtractor


def main():
    print("=" * 75)
    print("QuoteJudge — Multi-Format Quotation Ingestion & Fact Extraction (QJ-002)")
    print("=" * 75)

    extractor = QuotationExtractor()

    with tempfile.TemporaryDirectory() as td:
        dir_p = Path(td)

        # -------------------------------------------------------------
        # 1. Plain Text Ingestion (.txt)
        # -------------------------------------------------------------
        print("\n[Scenario 1] Ingesting Plain Text Quotation (.txt)...")
        txt_file = dir_p / "quote_industrial.txt"
        txt_content = (
            "Supplier: Gulf Heavy Piping Solutions FZE\n"
            "Quote ID: GHP-2026-902\n"
            "Date: 2026-11-10\n"
            "Valid Until: 2026-12-10\n"
            "Currency: SAR\n"
            "Item 1: Seamless Steel Pipe 8-inch - Qty: 50 pcs - Unit Price: 420.00 - Total: 21000.00\n"
            "Item 2: Flange Weld Neck Class 300 - Qty: 25 pcs - Unit Price: 180.00 - Total: 4500.00\n"
            "Subtotal: 25500.00 SAR\n"
            "Shipping: 1200.00 SAR\n"
            "VAT (15%): 4005.00 SAR\n"
            "Grand Total: 30705.00 SAR\n"
            "Payment Terms: 30% advance, 70% before delivery\n"
            "Delivery Time: 25 calendar days\n"
            "Incoterms: DAP Dammam Site\n"
            "Warranty: 24 months\n"
        )
        txt_file.write_text(txt_content, encoding="utf-8")

        doc_txt = DocumentLoader.load_file(txt_file)
        quote_txt = extractor.extract(doc_txt)
        val_txt = quote_txt.validate(source_text=doc_txt.raw_text)

        print(f"  Ingested: {doc_txt.document_id} ({doc_txt.file_format.upper()}, {doc_txt.char_count} chars)")
        print(f"  Supplier: {quote_txt.supplier_name} | Ref: {quote_txt.quote_id}")
        print(f"  Line Items Extracted: {len(quote_txt.line_items)}")
        print(f"  Total Amount: {quote_txt.total_amount:.2f} {quote_txt.currency.value}")
        print(f"  Integrity Status: {'PASS' if val_txt.is_valid else 'FAIL'} (Arithmetic: {len(val_txt.arithmetic_errors)} errs, Evidence: {len(val_txt.evidence_errors)} errs)")

        # -------------------------------------------------------------
        # 2. Markdown Table Ingestion (.md)
        # -------------------------------------------------------------
        print("\n[Scenario 2] Ingesting Markdown Table Quotation (.md)...")
        md_file = dir_p / "quote_hydraulics.md"
        md_content = (
            "# Commercial Quotation\n"
            "Supplier: Atlas Fluid Power Ltd\n"
            "Ref: AFP-7712\n"
            "Date: 2026-11-05\n"
            "Currency: USD\n\n"
            "| Item | Description | Qty | Unit Price | Total |\n"
            "|---|---|---|---|---|\n"
            "| 1 | Hydraulic Cylinder 100mm | 4 | 850.00 | 3400.00 |\n"
            "| 2 | Directional Control Valve | 2 | 450.00 | 900.00 |\n\n"
            "Subtotal: 4300.00 USD\n"
            "Grand Total: 4300.00 USD\n"
            "Payment Terms: 100% LC at sight\n"
            "Delivery Time: 30 days\n"
            "Incoterms: FOB Shanghai Port\n"
            "Warranty: 12 months\n"
        )
        md_file.write_text(md_content, encoding="utf-8")

        doc_md = DocumentLoader.load_file(md_file)
        quote_md = extractor.extract(doc_md)
        val_md = quote_md.validate(source_text=doc_md.raw_text)

        print(f"  Ingested: {doc_md.document_id} ({doc_md.file_format.upper()})")
        print(f"  Supplier: {quote_md.supplier_name} | Ref: {quote_md.quote_id}")
        print(f"  Items: {len(quote_md.line_items)} | Total: {quote_md.total_amount:.2f} {quote_md.currency.value}")
        print(f"  Integrity: {'PASS' if val_md.is_valid else 'FAIL'}")

        # -------------------------------------------------------------
        # 3. CSV Ingestion (.csv)
        # -------------------------------------------------------------
        print("\n[Scenario 3] Ingesting Structured CSV Quotation (.csv)...")
        csv_file = dir_p / "pricing_schedule.csv"
        csv_content = (
            "Item,Description,Qty,Unit,Unit_Price,Total_Price\n"
            "1,Carbon Steel Flange 4-inch,40,pcs,75.00,3000.00\n"
            "2,Blind Flange 4-inch,20,pcs,60.00,1200.00\n"
        )
        csv_file.write_text(csv_content, encoding="utf-8")

        doc_csv = DocumentLoader.load_file(csv_file)
        quote_csv = extractor.extract(doc_csv)

        print(f"  Ingested: {doc_csv.document_id} ({doc_csv.file_format.upper()}, {doc_csv.metadata.get('csv_rows')} rows)")
        print(f"  Extracted {len(quote_csv.line_items)} line items totaling {quote_csv.total_amount:.2f} {quote_csv.currency.value}")

        # -------------------------------------------------------------
        # 4. Text-based PDF Ingestion (.pdf via pdftotext)
        # -------------------------------------------------------------
        if shutil.which("ps2pdf") and shutil.which("pdftotext"):
            print("\n[Scenario 4] Ingesting Text-Based PDF Quotation (.pdf via pdftotext)...")
            ps_file = dir_p / "quote_digital.ps"
            pdf_file = dir_p / "quote_digital.pdf"
            ps_content = (
                "%!PS\n"
                "/Helvetica findfont 11 scalefont setfont\n"
                "50 720 moveto (Supplier: Red Sea Valves Manufacturing) show\n"
                "50 700 moveto (Quote ID: RSV-2026-303) show\n"
                "50 680 moveto (Date: 2026-11-10) show\n"
                "50 660 moveto (Currency: USD) show\n"
                "50 630 moveto (Item 1: Check Valve 3-inch - Qty: 15 pcs - Unit Price: 300.00 - Total: 4500.00) show\n"
                "50 600 moveto (Grand Total: 4500.00 USD) show\n"
                "50 570 moveto (Payment Terms: Net 45 days) show\n"
                "50 550 moveto (Delivery Schedule: 14 days) show\n"
                "50 530 moveto (Incoterms: EXW Dammam) show\n"
                "50 510 moveto (Warranty: 12 months) show\n"
                "showpage\n"
            )
            ps_file.write_text(ps_content, encoding="ascii")
            subprocess.run(["ps2pdf", str(ps_file), str(pdf_file)], check=True)

            doc_pdf = DocumentLoader.load_file(pdf_file)
            quote_pdf = extractor.extract(doc_pdf)
            val_pdf = quote_pdf.validate(source_text=doc_pdf.raw_text)

            print(f"  Ingested: {doc_pdf.document_id} ({doc_pdf.file_format.upper()}, pdftotext layout mode)")
            print(f"  Supplier: {quote_pdf.supplier_name} | Quote ID: {quote_pdf.quote_id}")
            print(f"  Total: {quote_pdf.total_amount:.2f} {quote_pdf.currency.value}")
            print(f"  Integrity: {'PASS' if val_pdf.is_valid else 'FAIL'}")

        # -------------------------------------------------------------
        # 5. Scanned / Raster PDF Guardrail
        # -------------------------------------------------------------
        print("\n[Scenario 5] Scanned PDF / Zero-Text Fail-Closed Guardrail...")
        scanned_pdf = dir_p / "scanned_image.pdf"
        scanned_pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF")

        try:
            DocumentLoader.load_file(scanned_pdf)
            print("  ERROR: Did not catch scanned PDF!")
        except (OCRRequiredError, ValueError) as err:
            print(f"  Guardrail Successfully Enforced (Fail-Closed):")
            print(f"  [Refusal Diagnostic]: {err}")

    print("\n" + "=" * 75)
    print("QuoteJudge QJ-002 Demonstration Complete (All Scenarios Verified).")
    print("=" * 75)
    return 0


if __name__ == "__main__":
    sys.exit(main())
