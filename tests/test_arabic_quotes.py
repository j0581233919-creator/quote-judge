"""Tests for Arabic supplier quotes, Arabic currency handling, and bilingual missing terms."""

from __future__ import annotations
import unittest
from quote_judge.models import (
    Currency,
    Incoterm,
    MissingTermCategory,
    EvidenceSpan,
    LineItem,
    Terms,
    Quotation,
)
from quote_judge.evidence import (
    locate_evidence,
    calculate_line_number,
    verify_evidence_span,
)


class TestArabicQuotation(unittest.TestCase):
    """Tests Arabic language quotations, Eastern numerals, and regional terms."""

    def setUp(self):
        self.arabic_quote_text = (
            "شركة الفنار للمقاولات والتوريدات العمومية\n"
            "عرض سعر رقم: ف-٢٠٢٦-٥٥٤\n"
            "التاريخ: 2026-11-10\n"
            "الصنف: كابل نحاس مسلح ٤*١٦ مم | الكمية: 500 متر | السعر الفردي: 45.00 ر.س | الإجمالي: 22500.00 ر.س\n"
            "الصنف: لوحة توزيع رئيسية 250 أمبير | الكمية: 2 قطعة | السعر الفردي: 3500.00 ر.س | الإجمالي: 7000.00 ر.س\n"
            "المجموع الفرعي: 29500.00 ر.س\n"
            "ضريبة القيمة المضافة (15%): 4425.00 ر.س\n"
            "الشحن والتوصيل: 500.00 ر.س\n"
            "الإجمالي النهائي: 34425.00 ر.س\n"
            "شروط الدفع: 50% دفعة مقدمة عند التعميد و 50% بعد الفحص والاستلام\n"
            "مدة التوريد: خلال 14 يوم عمل من استلام الدفعة المقدمة\n"
            "صلاحية العرض: العرض سارٍ لمدة 30 يوماً من تاريخه (حتى 2026-12-10)\n"
            "شروط التسليم: تسليم موقع المشروع بمدينة الرياض (DAP)\n"
            "الضمان: ضمان شامل لمدة 24 شهراً ضد عيوب الصناعة\n"
        )

    def test_arabic_evidence_extraction_and_grounding(self):
        supplier_target = "شركة الفنار للمقاولات والتوريدات العمومية"
        supplier_span = locate_evidence(self.arabic_quote_text, supplier_target, "doc_ar")
        self.assertIsNotNone(supplier_span)
        self.assertEqual(supplier_span.line_number, 1)
        self.assertTrue(supplier_span.verify(self.arabic_quote_text))

        quote_id_target = "ف-٢٠٢٦-٥٥٤"
        quote_id_span = locate_evidence(self.arabic_quote_text, quote_id_target, "doc_ar")
        self.assertIsNotNone(quote_id_span)
        self.assertEqual(quote_id_span.line_number, 2)
        self.assertTrue(quote_id_span.verify(self.arabic_quote_text))

        item1_target = "كابل نحاس مسلح ٤*١٦ مم"
        item1_span = locate_evidence(self.arabic_quote_text, item1_target, "doc_ar")
        self.assertIsNotNone(item1_span)
        self.assertEqual(item1_span.line_number, 4)
        self.assertTrue(item1_span.verify(self.arabic_quote_text))

    def test_arabic_quotation_full_validation(self):
        item1 = LineItem(
            item_id="1",
            description="كابل نحاس مسلح ٤*١٦ مم",
            quantity=500.0,
            unit_of_measure="متر",
            unit_price=45.0,
            total_price=22500.0,
            currency=Currency.SAR,
            item_evidence=locate_evidence(self.arabic_quote_text, "كابل نحاس مسلح ٤*١٦ مم", "doc_ar"),
            unit_price_evidence=locate_evidence(self.arabic_quote_text, "45.00 ر.س", "doc_ar"),
            total_price_evidence=locate_evidence(self.arabic_quote_text, "22500.00 ر.س", "doc_ar"),
        )

        item2 = LineItem(
            item_id="2",
            description="لوحة توزيع رئيسية 250 أمبير",
            quantity=2.0,
            unit_of_measure="قطعة",
            unit_price=3500.0,
            total_price=7000.0,
            currency=Currency.SAR,
            item_evidence=locate_evidence(self.arabic_quote_text, "لوحة توزيع رئيسية 250 أمبير", "doc_ar"),
            unit_price_evidence=locate_evidence(self.arabic_quote_text, "3500.00 ر.س", "doc_ar"),
            total_price_evidence=locate_evidence(self.arabic_quote_text, "7000.00 ر.س", "doc_ar"),
        )

        terms = Terms(
            payment_terms="50% دفعة مقدمة عند التعميد و 50% بعد الفحص والاستلام",
            delivery_lead_time_days=14,
            delivery_terms_description="خلال 14 يوم عمل من استلام الدفعة المقدمة",
            valid_until="2026-12-10",
            incoterm=Incoterm.DAP,
            named_place="موقع المشروع بمدينة الرياض",
            warranty_months=24,
            warranty_description="ضمان شامل لمدة 24 شهراً ضد عيوب الصناعة",
            is_tax_included=False,
            tax_rate=0.15,
            is_shipping_included=False,
            shipping_cost=500.0,
            minimum_order_quantity=1.0,
            evidence={
                "payment_terms": locate_evidence(
                    self.arabic_quote_text,
                    "50% دفعة مقدمة عند التعميد و 50% بعد الفحص والاستلام",
                    "doc_ar",
                ),
            },
        )

        quote = Quotation(
            quote_id="ف-٢٠٢٦-٥٥٤",
            supplier_name="شركة الفنار للمقاولات والتوريدات العمومية",
            currency=Currency.SAR,
            line_items=[item1, item2],
            subtotal=29500.0,
            tax_amount=4425.0,
            shipping_amount=500.0,
            total_amount=34425.0,
            terms=terms,
            raw_text=self.arabic_quote_text,
            document_id="doc_ar",
            quote_id_evidence=locate_evidence(self.arabic_quote_text, "ف-٢٠٢٦-٥٥٤", "doc_ar"),
            supplier_evidence=locate_evidence(
                self.arabic_quote_text,
                "شركة الفنار للمقاولات والتوريدات العمومية",
                "doc_ar",
            ),
            total_amount_evidence=locate_evidence(self.arabic_quote_text, "34425.00 ر.س", "doc_ar"),
        )

        result = quote.validate(source_text=self.arabic_quote_text)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.arithmetic_errors), 0)
        self.assertEqual(len(result.evidence_errors), 0)
        self.assertEqual(len(result.currency_mismatches), 0)
        self.assertEqual(len(result.missing_term_alerts), 0)

        # Ensure JSON serialization preserves Arabic unicode without escaping
        json_output = quote.to_json()
        self.assertIn("شركة الفنار للمقاولات والتوريدات العمومية", json_output)
        self.assertIn("كابل نحاس مسلح", json_output)

    def test_missing_terms_alert_bilingual_clarifications(self):
        sparse_terms = Terms(
            payment_terms="Net 60 days",
        )
        alerts = sparse_terms.detect_missing_terms()

        # Check Arabic clarification suggestions
        for alert in alerts:
            self.assertTrue(len(alert.suggested_clarification_ar) > 10)
            self.assertTrue(len(alert.suggested_clarification_en) > 10)


if __name__ == "__main__":
    unittest.main()
