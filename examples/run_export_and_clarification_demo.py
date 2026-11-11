#!/usr/bin/env python3
"""Demonstration of QuoteJudge QJ-004 bilingual clarification generator and secure multi-format exports."""

from __future__ import annotations
import sys
import tempfile
from pathlib import Path

# Ensure quote_judge package is resolvable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quote_judge.models import (
    Currency,
    Incoterm,
    LineItem,
    Terms,
    Quotation,
)
from quote_judge.comparator import QuotationComparator
from quote_judge.clarification import BilingualClarificationGenerator
from quote_judge.export import QuotationExporter


def main():
    print("=" * 80)
    print("QuoteJudge — Bilingual Clarification Generator & Export Engine (QJ-004)")
    print("=" * 80)

    # 1. Create Sample Competing Quotes with specific missing terms
    quote1 = Quotation(
        quote_id="Q-SA-881",
        supplier_name="Al-Yamamah Industrial Supply",
        currency=Currency.SAR,
        line_items=[
            LineItem("1", "Check Valve 4-inch Cl 300", 10.0, "pcs", 1200.0, 12000.0, Currency.SAR),
            LineItem("2", "Ball Valve 4-inch Cl 300", 15.0, "pcs", 1600.0, 24000.0, Currency.SAR),
        ],
        subtotal=36000.0,
        total_amount=36000.0,
        terms=Terms(
            payment_terms="30% advance, 70% before delivery",
            delivery_lead_time_days=15,
            valid_until="2026-12-15",
            incoterm=Incoterm.DAP,
            named_place="Riyadh Site",
            warranty_months=12,
            is_tax_included=False,
            is_shipping_included=True,
            minimum_order_quantity=5.0,
        ),
    )

    quote2 = Quotation(
        quote_id="Q-CN-904",
        supplier_name="Zhejiang Valve & Piping Co.",
        currency=Currency.USD,
        line_items=[
            LineItem("A", "Check Valve 4-inch Cl 300", 10.0, "pcs", 280.0, 2800.0, Currency.USD),
            LineItem("B", "Ball Valve 4-inch Cl 300", 15.0, "pcs", 370.0, 5550.0, Currency.USD),
        ],
        subtotal=8350.0,
        total_amount=8350.0,
        terms=Terms(
            # Omitted: payment terms, warranty, and Incoterms named place!
            delivery_lead_time_days=40,
            valid_until="2026-11-30",
            incoterm=Incoterm.FOB,
            is_tax_included=False,
            is_shipping_included=False,
        ),
    )

    comparator = QuotationComparator(
        exchange_rates={"USD": 3.75, "SAR": 1.0},
        base_currency="SAR",
    )
    report = comparator.compare([quote1, quote2])

    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td) / "export_output"
        out_dir.mkdir(parents=True, exist_ok=True)

        # 2. Export Comparison to CSV (with formula injection defense)
        print("\n[1] Exporting Comparison to Sanitized CSV...")
        csv_path = out_dir / "quotes_comparison.csv"
        QuotationExporter.export_comparison_to_csv(report, csv_path)
        print(f"  Created CSV: {csv_path.name} ({csv_path.stat().st_size} bytes)")

        # 3. Export Comparison to Markdown
        print("\n[2] Exporting Comparison to Markdown Report...")
        md_path = out_dir / "quotes_comparison.md"
        QuotationExporter.export_comparison_to_markdown(report, md_path)
        print(f"  Created Markdown: {md_path.name} ({md_path.stat().st_size} bytes)")

        # 4. Export Comparison to JSON
        print("\n[3] Exporting Comparison to JSON...")
        json_path = out_dir / "quotes_comparison.json"
        QuotationExporter.export_comparison_to_json(report, json_path)
        print(f"  Created JSON: {json_path.name} ({json_path.stat().st_size} bytes)")

        # 5. Generate and Export Bilingual Clarification Letters
        print("\n[4] Generating Bilingual Clarification Letters...")
        generator = BilingualClarificationGenerator(
            buyer_company="Saudi National Energy & Water Authority",
            contact_person="Eng. Khalid Al-Mansoor (Procurement Director)",
        )
        letters = generator.generate_letters_for_report(report)
        print(f"  Generated letters for {len(letters)} supplier(s) with missing terms.")

        letters_dir = out_dir / "clarification_letters"
        written = QuotationExporter.export_clarification_letters(letters, letters_dir, format="md")
        for p in written:
            print(f"  Wrote Letter: {p.name}")

        # Display preview of Zhejiang letter
        if "Zhejiang Valve & Piping Co." in letters:
            zhejiang_letter = letters["Zhejiang Valve & Piping Co."]
            print("\n" + "=" * 60)
            print("PREVIEW: BILINGUAL LETTER TO ZHEJIANG VALVE & PIPING CO.")
            print("=" * 60)
            print(zhejiang_letter.to_markdown("bilingual"))
            print("=" * 60)

    print("\n" + "=" * 80)
    print("QuoteJudge QJ-004 Demonstration Complete.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
