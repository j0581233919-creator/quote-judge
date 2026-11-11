#!/usr/bin/env python3
"""Runnable demonstration of QuoteJudge QJ-001 data models, evidence grounding, and missing terms auditor."""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure quote_judge package is resolvable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quote_judge.models import (
    Currency,
    Incoterm,
    EvidenceSpan,
    LineItem,
    Terms,
    Quotation,
)
from quote_judge.evidence import locate_evidence


def main():
    print("=" * 70)
    print("QuoteJudge — Supplier Quotation Data Models & Evidence Extraction Demo")
    print("=" * 70)

    # 1. Realistic Supplier Quotation Document
    quote_doc = (
        "----------------------------------------------------------------------\n"
        "QUOTATION DOCUMENT\n"
        "Supplier: Gulf Energy Equipment FZE\n"
        "Quotation Ref: GEE-2026-NOV-412\n"
        "Date: 2026-11-10\n"
        "Valid Until: 2026-12-10\n"
        "Currency: SAR\n"
        "----------------------------------------------------------------------\n"
        "LINE ITEMS:\n"
        "1. High-Pressure Ball Valve 4-inch Class 600\n"
        "   Qty: 20 pcs | Unit Price: 1,850.00 SAR | Total: 37,000.00 SAR\n"
        "2. Spiral Wound Gasket 4-inch Class 600\n"
        "   Qty: 40 pcs | Unit Price: 125.00 SAR | Total: 5,000.00 SAR\n"
        "----------------------------------------------------------------------\n"
        "Subtotal: 42,000.00 SAR\n"
        "Discount (Special Order Discount): 2,000.00 SAR\n"
        "Freight & Handling (Dammam Site Delivery): 1,500.00 SAR\n"
        "VAT (15%): 6,225.00 SAR\n"
        "Grand Total: 47,725.00 SAR\n"
        "----------------------------------------------------------------------\n"
        "COMMERCIAL TERMS:\n"
        "Payment Terms: 30% advance with order, 70% against delivery documents\n"
        "Delivery Schedule: 21 calendar days from advance payment receipt\n"
        "Delivery Terms: DAP Dammam Project Site (Incoterms 2020)\n"
        "Warranty: 18 months standard manufacturer warranty\n"
        "----------------------------------------------------------------------\n"
    )

    print("\n[1] Ingesting Raw Quotation Document...")
    print(f"Document Length: {len(quote_doc)} characters, {quote_doc.count(chr(10))} lines")

    # 2. Extract Evidence and Construct Typed Line Items
    print("\n[2] Extracting Typed Line Items with Exact Source Grounding...")
    item1 = LineItem(
        item_id="1",
        description="High-Pressure Ball Valve 4-inch Class 600",
        quantity=20.0,
        unit_of_measure="pcs",
        unit_price=1850.0,
        total_price=37000.0,
        currency=Currency.SAR,
        item_evidence=locate_evidence(quote_doc, "High-Pressure Ball Valve 4-inch Class 600", "quote_gee.txt"),
        unit_price_evidence=locate_evidence(quote_doc, "1,850.00 SAR", "quote_gee.txt"),
        total_price_evidence=locate_evidence(quote_doc, "37,000.00 SAR", "quote_gee.txt"),
    )

    item2 = LineItem(
        item_id="2",
        description="Spiral Wound Gasket 4-inch Class 600",
        quantity=40.0,
        unit_of_measure="pcs",
        unit_price=125.0,
        total_price=5000.0,
        currency=Currency.SAR,
        item_evidence=locate_evidence(quote_doc, "Spiral Wound Gasket 4-inch Class 600", "quote_gee.txt"),
        unit_price_evidence=locate_evidence(quote_doc, "125.00 SAR", "quote_gee.txt"),
        total_price_evidence=locate_evidence(quote_doc, "5,000.00 SAR", "quote_gee.txt"),
    )

    print(f"  Item 1: {item1.description} (Qty: {item1.quantity}, Unit: {item1.unit_price} {item1.currency.value})")
    print(f"    Line No: {item1.item_evidence.line_number}, Offsets: [{item1.item_evidence.start_char}:{item1.item_evidence.end_char}]")
    print(f"  Item 2: {item2.description} (Qty: {item2.quantity}, Unit: {item2.unit_price} {item2.currency.value})")
    print(f"    Line No: {item2.item_evidence.line_number}, Offsets: [{item2.item_evidence.start_char}:{item2.item_evidence.end_char}]")

    # 3. Construct Commercial Terms
    print("\n[3] Extracting Commercial Terms...")
    terms = Terms(
        payment_terms="30% advance with order, 70% against delivery documents",
        delivery_lead_time_days=21,
        delivery_terms_description="21 calendar days from advance payment receipt",
        valid_until="2026-12-10",
        incoterm=Incoterm.DAP,
        named_place="Dammam Project Site",
        warranty_months=18,
        warranty_description="18 months standard manufacturer warranty",
        is_tax_included=False,
        tax_rate=0.15,
        is_shipping_included=False,
        shipping_cost=1500.0,
        evidence={
            "payment_terms": locate_evidence(
                quote_doc,
                "30% advance with order, 70% against delivery documents",
                "quote_gee.txt",
            ),
            "incoterm": locate_evidence(
                quote_doc,
                "DAP Dammam Project Site (Incoterms 2020)",
                "quote_gee.txt",
            ),
        },
    )

    # 4. Construct Quotation Aggregate
    quote = Quotation(
        quote_id="GEE-2026-NOV-412",
        supplier_name="Gulf Energy Equipment FZE",
        quote_date="2026-11-10",
        valid_until="2026-12-10",
        currency=Currency.SAR,
        line_items=[item1, item2],
        subtotal=42000.0,
        discount_amount=2000.0,
        shipping_amount=1500.0,
        tax_amount=6225.0,
        total_amount=47725.0,
        terms=terms,
        raw_text=quote_doc,
        document_id="quote_gee.txt",
        quote_id_evidence=locate_evidence(quote_doc, "GEE-2026-NOV-412", "quote_gee.txt"),
        supplier_evidence=locate_evidence(quote_doc, "Gulf Energy Equipment FZE", "quote_gee.txt"),
        total_amount_evidence=locate_evidence(quote_doc, "47,725.00 SAR", "quote_gee.txt"),
    )

    # 5. Execute Mathematical & Evidentiary Validation
    print("\n[4] Validating Mathematical and Evidentiary Integrity...")
    validation = quote.validate(source_text=quote_doc)
    print(f"  Integrity Status: {'PASS (100% Consistent)' if validation.is_valid else 'FAIL'}")
    print(f"  Arithmetic Errors: {len(validation.arithmetic_errors)}")
    print(f"  Evidence Mismatches: {len(validation.evidence_errors)}")
    print(f"  Currency Desyncs: {len(validation.currency_mismatches)}")

    # 6. Audit Missing Terms
    print("\n[5] Auditing Missing Commercial Terms & Formulating Bilingual Clarifications...")
    missing_alerts = validation.missing_term_alerts
    if missing_alerts:
        print(f"  Detected {len(missing_alerts)} missing/ambiguous term(s):")
        for idx, alert in enumerate(missing_alerts, 1):
            print(f"    [{idx}] {alert.category.value} ({alert.severity})")
            print(f"        EN: {alert.description_en}")
            print(f"        AR: {alert.description_ar}")
            print(f"        Question (EN): {alert.suggested_clarification_en}")
            print(f"        سؤال المورد (عربي): {alert.suggested_clarification_ar}")
    else:
        print("  All essential commercial terms are fully specified and grounded.")

    print("\n" + "=" * 70)
    print("QuoteJudge QJ-001 Demonstration Complete.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
