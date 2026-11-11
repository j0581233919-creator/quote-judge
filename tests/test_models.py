"""Tests for QuoteJudge data models, arithmetic integrity, and missing terms auditor."""

from __future__ import annotations
import json
import unittest
from quote_judge.models import (
    Currency,
    Incoterm,
    MissingTermCategory,
    MissingTermAlert,
    EvidenceSpan,
    LineItem,
    Terms,
    Quotation,
    QuotationValidationResult,
)


class TestModels(unittest.TestCase):
    """Unit and behavioral tests for core schemas in QuoteJudge."""

    def test_currency_normalization(self):
        self.assertEqual(Currency.normalize("USD"), Currency.USD)
        self.assertEqual(Currency.normalize("$"), Currency.USD)
        self.assertEqual(Currency.normalize("SAR"), Currency.SAR)
        self.assertEqual(Currency.normalize("ريال"), Currency.SAR)
        self.assertEqual(Currency.normalize("ر.س"), Currency.SAR)
        self.assertEqual(Currency.normalize("AED"), Currency.AED)
        self.assertEqual(Currency.normalize("درهم"), Currency.AED)
        self.assertEqual(Currency.normalize("EUR"), Currency.EUR)
        self.assertEqual(Currency.normalize("€"), Currency.EUR)
        self.assertEqual(Currency.normalize("GBP"), Currency.GBP)
        self.assertEqual(Currency.normalize("£"), Currency.GBP)
        self.assertEqual(Currency.normalize("EGP"), Currency.EGP)
        self.assertEqual(Currency.normalize("جنيه"), Currency.EGP)
        self.assertEqual(Currency.normalize("UNKNOWN_XYZ"), Currency.OTHER)
        self.assertEqual(Currency.normalize(None), Currency.OTHER)

    def test_incoterm_normalization(self):
        self.assertEqual(Incoterm.normalize("FOB"), Incoterm.FOB)
        self.assertEqual(Incoterm.normalize("free on board"), Incoterm.FOB)
        self.assertEqual(Incoterm.normalize("EXW"), Incoterm.EXW)
        self.assertEqual(Incoterm.normalize("ex-works"), Incoterm.EXW)
        self.assertEqual(Incoterm.normalize("CIF"), Incoterm.CIF)
        self.assertEqual(Incoterm.normalize("DDP"), Incoterm.DDP)
        self.assertEqual(Incoterm.normalize("INVALID_INCO"), Incoterm.UNSPECIFIED)
        self.assertEqual(Incoterm.normalize(None), Incoterm.UNSPECIFIED)

    def test_evidence_span_validation_and_verification(self):
        sample_doc = "QUOTATION #Q-2026-99\nSupplier: Gulf Heavy Industries Ltd.\nTotal Price: 45000.00 USD"

        # Valid span
        span = EvidenceSpan(
            document_id="doc1",
            start_char=11,
            end_char=20,
            exact_text="Q-2026-99",
            page_number=1,
            line_number=1,
        )
        self.assertTrue(span.verify(sample_doc))

        # Serialization roundtrip
        span_dict = span.to_dict()
        restored_span = EvidenceSpan.from_dict(span_dict)
        self.assertEqual(restored_span.start_char, span.start_char)
        self.assertEqual(restored_span.end_char, span.end_char)
        self.assertEqual(restored_span.exact_text, span.exact_text)
        self.assertEqual(restored_span.page_number, 1)

        # Mismatched text fails verification
        tampered_span = EvidenceSpan(
            document_id="doc1",
            start_char=11,
            end_char=20,
            exact_text="Q-2026-00",  # wrong text
        )
        self.assertFalse(tampered_span.verify(sample_doc))

        # Invalid offset boundaries raise ValueError
        with self.assertRaises(ValueError):
            EvidenceSpan(document_id="doc1", start_char=-1, end_char=5, exact_text="test")
        with self.assertRaises(ValueError):
            EvidenceSpan(document_id="doc1", start_char=10, end_char=5, exact_text="test")
        with self.assertRaises(ValueError):
            EvidenceSpan(document_id="doc1", start_char=0, end_char=2, exact_text="te", page_number=0)

    def test_line_item_arithmetic_consistency(self):
        # Consistent line item
        item = LineItem(
            item_id="1",
            description="Industrial Centrifugal Pump 50HP",
            quantity=3.0,
            unit_of_measure="pcs",
            unit_price=12000.0,
            total_price=36000.0,
            currency=Currency.USD,
        )
        is_ok, err = item.is_arithmetically_consistent()
        self.assertTrue(is_ok)
        self.assertIsNone(err)

        # Consistent line item with discount
        item_discounted = LineItem(
            item_id="2",
            description="High Pressure Flange Valve",
            quantity=10.0,
            unit_price=500.0,
            discount=500.0,
            total_price=4500.0,
            currency=Currency.USD,
        )
        is_ok, err = item_discounted.is_arithmetically_consistent()
        self.assertTrue(is_ok)
        self.assertIsNone(err)

        # Inconsistent line item
        inconsistent_item = LineItem(
            item_id="3",
            description="Pressure Sensor Unit",
            quantity=5.0,
            unit_price=200.0,
            total_price=1200.0,  # 5 * 200 = 1000, mismatch!
            currency=Currency.USD,
        )
        is_ok, err = inconsistent_item.is_arithmetically_consistent()
        self.assertFalse(is_ok)
        self.assertIn("Arithmetic mismatch", err)

        # Line item roundtrip
        item_dict = item.to_dict()
        restored = LineItem.from_dict(item_dict)
        self.assertEqual(restored.item_id, item.item_id)
        self.assertEqual(restored.total_price, item.total_price)
        self.assertEqual(restored.currency, Currency.USD)

    def test_line_item_non_negative_validation(self):
        with self.assertRaises(ValueError):
            LineItem(
                item_id="err",
                description="Faulty Item",
                quantity=-5.0,
                unit_price=10.0,
                total_price=50.0,
            )
        with self.assertRaises(ValueError):
            LineItem(
                item_id="err",
                description="Faulty Item",
                quantity=5.0,
                unit_price=-10.0,
                total_price=50.0,
            )

    def test_terms_missing_detection(self):
        # Empty terms -> should flag missing terms across critical categories
        empty_terms = Terms()
        alerts = empty_terms.detect_missing_terms()

        categories = {a.category for a in alerts}
        self.assertIn(MissingTermCategory.PAYMENT_TERMS, categories)
        self.assertIn(MissingTermCategory.DELIVERY_LEAD_TIME, categories)
        self.assertIn(MissingTermCategory.VALIDITY_PERIOD, categories)
        self.assertIn(MissingTermCategory.INCOTERM, categories)
        self.assertIn(MissingTermCategory.WARRANTY, categories)
        self.assertIn(MissingTermCategory.TAX_INCLUSION, categories)
        self.assertIn(MissingTermCategory.SHIPPING_INCLUSION, categories)
        self.assertIn(MissingTermCategory.MINIMUM_ORDER_QTY, categories)

        # Verify bilingual content in alerts
        payment_alert = next(a for a in alerts if a.category == MissingTermCategory.PAYMENT_TERMS)
        self.assertTrue(len(payment_alert.description_en) > 0)
        self.assertTrue(len(payment_alert.description_ar) > 0)
        self.assertTrue(len(payment_alert.suggested_clarification_en) > 0)
        self.assertTrue(len(payment_alert.suggested_clarification_ar) > 0)
        self.assertEqual(payment_alert.severity, "CRITICAL")

        # Fully specified terms -> zero missing terms alerts
        complete_terms = Terms(
            payment_terms="100% LC at sight",
            delivery_lead_time_days=45,
            valid_until="2026-12-31",
            incoterm=Incoterm.CIF,
            named_place="Jammam Port",
            warranty_months=24,
            is_tax_included=False,
            tax_rate=0.15,
            is_shipping_included=True,
            shipping_cost=1500.0,
            minimum_order_quantity=100.0,
        )
        complete_alerts = complete_terms.detect_missing_terms()
        self.assertEqual(len(complete_alerts), 0)

    def test_quotation_full_validation_and_integrity(self):
        raw_quote_text = (
            "SUPPLIER: Atlas Piping Solutions FZE\n"
            "QUOTE ID: AT-2026-781\n"
            "DATE: 2026-11-10\n"
            "ITEM 1: Seamless Steel Pipe 6 inch - QTY: 100 pcs - UNIT: 150.00 USD - TOTAL: 15000.00 USD\n"
            "ITEM 2: Flange Class 300 - QTY: 50 pcs - UNIT: 80.00 USD - TOTAL: 4000.00 USD\n"
            "SUBTOTAL: 19000.00 USD\n"
            "SHIPPING: 1000.00 USD\n"
            "VAT: 0.00 USD\n"
            "GRAND TOTAL: 20000.00 USD\n"
            "PAYMENT: 30% advance, 70% before delivery\n"
            "DELIVERY: 30 days Ex-Works Dammam\n"
            "VALIDITY: 2026-12-15\n"
        )

        from quote_judge.evidence import locate_evidence

        item1 = LineItem(
            item_id="1",
            description="Seamless Steel Pipe 6 inch",
            quantity=100.0,
            unit_price=150.0,
            total_price=15000.0,
            currency=Currency.USD,
            item_evidence=locate_evidence(raw_quote_text, "Seamless Steel Pipe 6 inch", "doc1"),
            total_price_evidence=locate_evidence(raw_quote_text, "15000.00 USD", "doc1"),
        )
        item2 = LineItem(
            item_id="2",
            description="Flange Class 300",
            quantity=50.0,
            unit_price=80.0,
            total_price=4000.0,
            currency=Currency.USD,
            item_evidence=locate_evidence(raw_quote_text, "Flange Class 300", "doc1"),
            total_price_evidence=locate_evidence(raw_quote_text, "4000.00 USD", "doc1"),
        )

        terms = Terms(
            payment_terms="30% advance, 70% before delivery",
            delivery_lead_time_days=30,
            valid_until="2026-12-15",
            incoterm=Incoterm.EXW,
            named_place="Dammam",
            warranty_months=12,
            is_tax_included=False,
            is_shipping_included=False,
            shipping_cost=1000.0,
            minimum_order_quantity=50.0,
            evidence={
                "payment_terms": locate_evidence(raw_quote_text, "30% advance, 70% before delivery", "doc1"),
            },
        )

        quote = Quotation(
            quote_id="AT-2026-781",
            supplier_name="Atlas Piping Solutions FZE",
            currency=Currency.USD,
            line_items=[item1, item2],
            subtotal=19000.0,
            shipping_amount=1000.0,
            tax_amount=0.0,
            discount_amount=0.0,
            total_amount=20000.0,
            terms=terms,
            raw_text=raw_quote_text,
            quote_id_evidence=locate_evidence(raw_quote_text, "AT-2026-781", "doc1"),
            supplier_evidence=locate_evidence(raw_quote_text, "Atlas Piping Solutions FZE", "doc1"),
            total_amount_evidence=locate_evidence(raw_quote_text, "20000.00 USD", "doc1"),
        )

        # Validate consistent quote
        result = quote.validate(source_text=raw_quote_text)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.arithmetic_errors), 0)
        self.assertEqual(len(result.evidence_errors), 0)
        self.assertEqual(len(result.currency_mismatches), 0)
        self.assertEqual(len(result.missing_term_alerts), 0)

        # JSON roundtrip
        json_str = quote.to_json()
        quote_restored = Quotation.from_json(json_str)
        self.assertEqual(quote_restored.quote_id, "AT-2026-781")
        self.assertEqual(quote_restored.total_amount, 20000.0)
        self.assertEqual(len(quote_restored.line_items), 2)
        self.assertEqual(quote_restored.terms.incoterm, Incoterm.EXW)

    def test_quotation_detects_subtotal_and_total_mismatches(self):
        item1 = LineItem(
            item_id="1",
            description="Item A",
            quantity=2.0,
            unit_price=100.0,
            total_price=200.0,
            currency=Currency.SAR,
        )
        item2 = LineItem(
            item_id="2",
            description="Item B",
            quantity=1.0,
            unit_price=300.0,
            total_price=300.0,
            currency=Currency.SAR,
        )

        # Subtotal stated as 600.00 when sum of items is 500.00
        quote = Quotation(
            quote_id="ERR-01",
            supplier_name="Defective Supplier",
            currency=Currency.SAR,
            line_items=[item1, item2],
            subtotal=600.0,  # MISMATCH
            total_amount=600.0,
        )
        result = quote.validate()
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Subtotal mismatch" in e for e in result.arithmetic_errors))

        # Total amount stated as 700.00 when subtotal(500) + tax(50) = 550.00
        quote2 = Quotation(
            quote_id="ERR-02",
            supplier_name="Defective Supplier 2",
            currency=Currency.SAR,
            line_items=[item1, item2],
            subtotal=500.0,
            tax_amount=50.0,
            total_amount=700.0,  # MISMATCH (expected 550)
        )
        result2 = quote2.validate()
        self.assertFalse(result2.is_valid)
        self.assertTrue(any("Total amount mismatch" in e for e in result2.arithmetic_errors))

    def test_quotation_detects_currency_mismatch(self):
        item_sar = LineItem(
            item_id="1",
            description="Local Item",
            quantity=1.0,
            unit_price=100.0,
            total_price=100.0,
            currency=Currency.SAR,
        )
        item_usd = LineItem(
            item_id="2",
            description="Imported Item",
            quantity=1.0,
            unit_price=50.0,
            total_price=50.0,
            currency=Currency.USD,  # Different currency!
        )
        quote = Quotation(
            quote_id="CURR-01",
            supplier_name="Multi-Currency Supplier",
            currency=Currency.SAR,
            line_items=[item_sar, item_usd],
            subtotal=150.0,
            total_amount=150.0,
        )
        result = quote.validate()
        self.assertFalse(result.is_valid)
        self.assertTrue(any("differs from quote currency" in m for m in result.currency_mismatches))


if __name__ == "__main__":
    unittest.main()
