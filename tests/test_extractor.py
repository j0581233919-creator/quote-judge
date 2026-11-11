"""Tests for QuoteJudge deterministic quotation extractor and evidence grounding."""

from __future__ import annotations
import unittest
from quote_judge.models import Currency, Incoterm
from quote_judge.parser import DocumentLoader
from quote_judge.extractor import QuotationExtractor


class TestQuotationExtractor(unittest.TestCase):
    """Verifies automated extraction across plain text, CSV, Markdown tables, and Arabic quotations."""

    def setUp(self):
        self.extractor = QuotationExtractor()

    def test_extract_standard_industrial_quote(self):
        text = (
            "Supplier: Gulf Energy Equipment FZE\n"
            "Quote ID: GEE-2026-NOV-412\n"
            "Date: 2026-11-10\n"
            "Valid Until: 2026-12-10\n"
            "Currency: SAR\n"
            "LINE ITEMS:\n"
            "Item 1: High-Pressure Ball Valve 4-inch - Qty: 20 pcs - Unit Price: 1850.00 - Total: 37000.00\n"
            "Item 2: Spiral Wound Gasket 4-inch - Qty: 40 pcs - Unit Price: 125.00 - Total: 5000.00\n"
            "Subtotal: 42,000.00 SAR\n"
            "Discount: 2,000.00 SAR\n"
            "Shipping: 1,500.00 SAR\n"
            "VAT (15%): 6,225.00 SAR\n"
            "Grand Total: 47,725.00 SAR\n"
            "Payment Terms: 30% advance with order, 70% against delivery documents\n"
            "Delivery Schedule: 21 calendar days from advance payment receipt\n"
            "Delivery Terms: DAP Dammam Site\n"
            "Warranty: 18 months standard manufacturer warranty\n"
            "MOQ: 10\n"
        )

        quote = self.extractor.extract(text, document_id="gee_quote.txt")

        # Identity & Metadata
        self.assertEqual(quote.supplier_name, "Gulf Energy Equipment FZE")
        self.assertEqual(quote.quote_id, "GEE-2026-NOV-412")
        self.assertEqual(quote.currency, Currency.SAR)
        self.assertEqual(quote.quote_date, "2026-11-10")
        self.assertEqual(quote.valid_until, "2026-12-10")

        # Line items
        self.assertEqual(len(quote.line_items), 2)
        self.assertEqual(quote.line_items[0].description, "High-Pressure Ball Valve 4-inch")
        self.assertEqual(quote.line_items[0].quantity, 20.0)
        self.assertEqual(quote.line_items[0].unit_price, 1850.0)
        self.assertEqual(quote.line_items[0].total_price, 37000.0)

        # Totals
        self.assertEqual(quote.subtotal, 42000.0)
        self.assertEqual(quote.discount_amount, 2000.0)
        self.assertEqual(quote.shipping_amount, 1500.0)
        self.assertEqual(quote.tax_amount, 6225.0)
        self.assertEqual(quote.total_amount, 47725.0)

        # Terms
        self.assertEqual(quote.terms.payment_terms, "30% advance with order, 70% against delivery documents")
        self.assertEqual(quote.terms.delivery_lead_time_days, 21)
        self.assertEqual(quote.terms.incoterm, Incoterm.DAP)
        self.assertEqual(quote.terms.named_place, "Dammam Site")
        self.assertEqual(quote.terms.warranty_months, 18)
        self.assertEqual(quote.terms.minimum_order_quantity, 10.0)

        # Validate whole quotation integrity
        validation = quote.validate(source_text=text)
        self.assertTrue(validation.is_valid)
        self.assertEqual(len(validation.arithmetic_errors), 0)
        self.assertEqual(len(validation.evidence_errors), 0)

    def test_extract_markdown_table_quote(self):
        text = (
            "# Commercial Offer\n"
            "Supplier: Precision Hydraulics Corp\n"
            "Ref: PHC-8891\n"
            "Date: 2026-10-15\n"
            "| Item | Description | Qty | Unit Price | Total |\n"
            "|---|---|---|---|---|\n"
            "| 1 | Hydraulic Hose 2m | 10 | 45.00 | 450.00 |\n"
            "| 2 | Quick Coupling Male | 20 | 15.00 | 300.00 |\n"
            "Grand Total: 750.00 USD\n"
            "Payment Terms: Net 30 days\n"
            "Delivery Time: 7 days\n"
            "Incoterms: EXW\n"
        )

        quote = self.extractor.extract(text, document_id="table_quote.md")
        self.assertEqual(quote.supplier_name, "Precision Hydraulics Corp")
        self.assertEqual(quote.quote_id, "PHC-8891")
        self.assertEqual(len(quote.line_items), 2)
        self.assertEqual(quote.line_items[0].description, "Hydraulic Hose 2m")
        self.assertEqual(quote.line_items[0].total_price, 450.00)
        self.assertEqual(quote.total_amount, 750.00)
        self.assertEqual(quote.terms.incoterm, Incoterm.EXW)
        self.assertEqual(quote.terms.payment_terms, "Net 30 days")

        validation = quote.validate(source_text=text)
        self.assertTrue(validation.is_valid)

    def test_extract_csv_structured_quote(self):
        csv_text = (
            "Item,Description,Qty,Unit,Unit_Price,Total_Price\n"
            "1,Carbon Steel Flange 2-inch,50,pcs,30.00,1500.00\n"
            "2,Spiral Gasket 2-inch,100,pcs,10.00,1000.00\n"
        )

        loaded_doc = DocumentLoader.load_text(csv_text, document_id="pricing.csv", file_format="csv")
        quote = self.extractor.extract(loaded_doc)

        self.assertEqual(len(quote.line_items), 2)
        self.assertEqual(quote.line_items[0].description, "Carbon Steel Flange 2-inch")
        self.assertEqual(quote.line_items[0].quantity, 50.0)
        self.assertEqual(quote.line_items[0].unit_price, 30.0)
        self.assertEqual(quote.line_items[0].total_price, 1500.0)
        self.assertEqual(quote.total_amount, 2500.0)

    def test_extract_arabic_quote(self):
        arabic_text = (
            "المورد: شركة الفنار للمقاولات والتوريدات العمومية\n"
            "رقم العرض: ف-2026-991\n"
            "التاريخ: 2026-11-10\n"
            "الصنف: كابل نحاس مسلح | الكمية: 200 متر | السعر الفردي: 50.00 ر.س | الإجمالي: 10000.00\n"
            "المجموع الفرعي: 10000.00 ر.س\n"
            "ضريبة القيمة المضافة: 1500.00 ر.س\n"
            "الإجمالي النهائي: 11500.00 ر.س\n"
            "شروط الدفع: 50% دفعة مقدمة والباقي عند التسليم\n"
            "شروط التسليم: تسليم موقع المشروع بمدينة الرياض (DAP)\n"
            "مدة التوريد: خلال 14 يوماً عمل\n"
            "الضمان: ضمان شامل لمدة 24 شهراً ضد عيوب الصناعة\n"
        )

        quote = self.extractor.extract(arabic_text, document_id="arabic_quote.txt")
        self.assertEqual(quote.supplier_name, "شركة الفنار للمقاولات والتوريدات العمومية")
        self.assertEqual(quote.quote_id, "ف-2026-991")
        self.assertEqual(quote.currency, Currency.SAR)
        self.assertEqual(len(quote.line_items), 1)
        self.assertEqual(quote.line_items[0].description, "كابل نحاس مسلح")
        self.assertEqual(quote.line_items[0].total_price, 10000.0)
        self.assertEqual(quote.total_amount, 11500.0)
        self.assertEqual(quote.terms.incoterm, Incoterm.DAP)
        self.assertEqual(quote.terms.warranty_months, 24)
        self.assertEqual(quote.terms.delivery_lead_time_days, 14)

        validation = quote.validate(source_text=arabic_text)
        self.assertTrue(validation.is_valid)

    def test_extract_empty_text_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.extractor.extract("   \n\t  ")


if __name__ == "__main__":
    unittest.main()
