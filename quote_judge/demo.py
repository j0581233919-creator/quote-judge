"""Self-contained interactive and automated demonstration for QuoteJudge.

Demonstrates:
- Multi-supplier quotation comparison (Saudi SAR, UAE AED, Chinese USD).
- Currency normalization with explicit caller-provided exchange rates.
- Missing commercial terms audit (omitted warranty, unconfirmed shipping/tax).
- Weighted multi-criteria scoring (price, delivery, warranty, completeness).
- Side-by-side markdown comparison matrix.
- Bilingual clarification letters for suppliers with missing terms.
"""

from __future__ import annotations
import sys
from typing import Dict, List

from .models import Currency, Incoterm, LineItem, Terms, Quotation
from .comparator import QuotationComparator
from .clarification import BilingualClarificationGenerator


def build_sample_quotations() -> List[Quotation]:
    """Builds three realistic competing supplier quotations for demonstration."""
    # Supplier 1: Local Saudi Supplier (DAP Dammam, high price, fast delivery, 24 mo warranty)
    quote1 = Quotation(
        quote_id="Q-DAMMAM-101",
        supplier_name="Al-Sharqiyah Industrial Supply Ltd",
        currency=Currency.SAR,
        line_items=[
            LineItem("1", "High-Pressure Ball Valve 4-inch Class 600", 20.0, "pcs", 1950.0, 39000.0, Currency.SAR),
            LineItem("2", "Spiral Wound Gasket 4-inch Class 600", 40.0, "pcs", 130.0, 5200.0, Currency.SAR),
        ],
        subtotal=44200.0,
        shipping_amount=0.0,
        tax_amount=6630.0,
        total_amount=50830.0,
        terms=Terms(
            payment_terms="30% advance, 70% within 30 days after delivery",
            delivery_lead_time_days=10,
            valid_until="2026-12-15",
            incoterm=Incoterm.DAP,
            named_place="Dammam Project Site",
            warranty_months=24,
            is_tax_included=False,
            is_shipping_included=True,
            minimum_order_quantity=5.0,
        ),
    )

    # Supplier 2: UAE Regional Supplier (FOB Jebel Ali, lower price, 21 days lead time, 12 mo warranty)
    quote2 = Quotation(
        quote_id="Q-DUBAI-442",
        supplier_name="Gulf Valve & Pipeline FZE",
        currency=Currency.AED,
        line_items=[
            LineItem("ITM-1", "4-inch Ball Valve High Pressure Class 600", 20.0, "pcs", 1750.0, 35000.0, Currency.AED),
            LineItem("ITM-2", "Spiral Gasket 4-inch Cl 600", 40.0, "pcs", 110.0, 4400.0, Currency.AED),
        ],
        subtotal=39400.0,
        total_amount=39400.0,
        terms=Terms(
            payment_terms="100% LC at sight",
            delivery_lead_time_days=21,
            valid_until="2026-12-10",
            incoterm=Incoterm.FOB,
            named_place="Jebel Ali Port",
            warranty_months=12,
            is_tax_included=False,
            is_shipping_included=False,
        ),
    )

    # Supplier 3: Chinese Manufacturer (EXW Shanghai, lowest unit price, 45 days delivery, missing warranty)
    quote3 = Quotation(
        quote_id="Q-SHA-992",
        supplier_name="Oriental Flow Controls Corp",
        currency=Currency.USD,
        line_items=[
            LineItem("A", "Ball Valve 4 inch #600", 20.0, "pcs", 380.0, 7600.0, Currency.USD),
            LineItem("B", "Gasket Spiral Wound 4 inch", 40.0, "pcs", 22.0, 880.0, Currency.USD),
        ],
        subtotal=8480.0,
        total_amount=8480.0,
        terms=Terms(
            payment_terms="30% TT advance, 70% before shipment",
            delivery_lead_time_days=45,
            valid_until="2026-11-30",
            incoterm=Incoterm.EXW,
            named_place="Shanghai Factory",
            warranty_months=None,  # Missing warranty!
            is_tax_included=False,
            is_shipping_included=False,
        ),
    )

    return [quote1, quote2, quote3]


def run_demo() -> int:
    """Runs a complete end-to-end demonstration."""
    print("=" * 80)
    print("QuoteJudge — Multi-Supplier Comparative Quotation Engine & Missing Terms Auditor")
    print("=" * 80)

    quotes = build_sample_quotations()
    print(f"Loaded {len(quotes)} sample competing quotations:")
    for q in quotes:
        print(f"  • [{q.quote_id}] {q.supplier_name} — {q.total_amount:,.2f} {q.currency.value}")

    print("\n[Step 1] Running Comparison Engine with Explicit Currency Exchange Rates...")
    rates = {
        "SAR": 1.0,
        "AED": 1.02,
        "USD": 3.75,
    }
    comparator = QuotationComparator(
        exchange_rates=rates,
        base_currency="SAR",
        price_weight=0.45,
        delivery_weight=0.25,
        warranty_weight=0.15,
        completeness_weight=0.15,
    )

    report = comparator.compare(quotes)
    print("\n" + report.to_markdown_table())

    print("\n" + "=" * 80)
    print(f"Overall Best Ranked Supplier: {report.best_overall_supplier}")
    print(f"Fastest Delivery:             {report.fastest_delivery_supplier} ({report.terms_comparison.delivery_lead_time_days.get(report.fastest_delivery_supplier)} days)")
    print(f"Longest Warranty:             {report.longest_warranty_supplier} ({report.terms_comparison.warranty_months.get(report.longest_warranty_supplier)} months)")
    print(f"Lowest Total Cost:            {report.lowest_total_cost_supplier}")
    print("=" * 80)

    print("\n[Step 2] Auditing Missing Commercial Terms & Generating Clarification Letters...")
    generator = BilingualClarificationGenerator(
        buyer_company="Al-Etihad Contracting & Trading Co.",
        contact_person="Eng. Tariq Al-Mansoor (Procurement Director)",
    )
    letters = generator.generate_letters_for_report(report)
    print(f"Generated {len(letters)} clarification letter(s) for suppliers with missing/ambiguous terms:")
    for sup_name, l in letters.items():
        print(f"\n--- [Supplier: {l.supplier_name} | Quote: {l.quote_id}] ---")
        print(f"Subject: {l.subject_en} / {l.subject_ar}")
        print(f"Questions identified: {len(l.questions)}")
        for idx, q in enumerate(l.questions, 1):
            print(f"  {idx}. [{q.category}] {q.question_en}")
            print(f"     {q.question_ar}")

    print("\n" + "=" * 80)
    print("Demo completed successfully. Zero hallucinated currencies or simulated OCR.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(run_demo())
