#!/usr/bin/env python3
"""Demonstration of QuoteJudge QJ-003 Comparative Quotation Engine & Missing Terms Auditor."""

from __future__ import annotations
import sys
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


def main():
    print("=" * 80)
    print("QuoteJudge — Multi-Supplier Comparative Quotation Engine (QJ-003)")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. Prepare 3 Competing Supplier Quotations
    # -------------------------------------------------------------
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
        shipping_amount=0.0,  # Free/included
        tax_amount=6630.0,
        total_amount=50830.0,
        terms=Terms(
            payment_terms="30% advance, 70% within 30 days after delivery",
            delivery_lead_time_days=10,  # 10 days!
            valid_until="2026-12-15",
            incoterm=Incoterm.DAP,
            named_place="Dammam Project Site",
            warranty_months=24,  # 2 years warranty!
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
            is_shipping_included=False,  # Excluded!
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

    quotes = [quote1, quote2, quote3]

    # -------------------------------------------------------------
    # 2. Compare with Explicit Exchange Rates
    # -------------------------------------------------------------
    print("\n[Step 1] Running Multi-Supplier Comparator with Explicit Exchange Rates...")
    rates = {
        "SAR": 1.0,
        "AED": 1.02,   # 1 AED = 1.02 SAR
        "USD": 3.75,   # 1 USD = 3.75 SAR
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

    # -------------------------------------------------------------
    # 3. Print Formatted Markdown Comparison Summary
    # -------------------------------------------------------------
    print("\n" + report.to_markdown_table())

    print("\n" + "=" * 80)
    print(f"Overall Best Ranked Supplier: {report.best_overall_supplier}")
    print(f"Fastest Delivery:             {report.fastest_delivery_supplier} ({report.terms_comparison.delivery_lead_time_days.get(report.fastest_delivery_supplier)} days)")
    print(f"Longest Warranty:             {report.longest_warranty_supplier} ({report.terms_comparison.warranty_months.get(report.longest_warranty_supplier)} months)")
    print(f"Lowest Total Cost:            {report.lowest_total_cost_supplier}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
