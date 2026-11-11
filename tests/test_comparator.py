"""Tests for QuoteJudge Comparative Quotation Engine and Missing Terms Auditor."""

from __future__ import annotations
import unittest
from quote_judge.models import (
    Currency,
    Incoterm,
    LineItem,
    Terms,
    Quotation,
)
from quote_judge.comparator import (
    QuotationComparator,
    token_similarity,
    tokenize_product_name,
)


class TestQuotationComparator(unittest.TestCase):
    """Verifies cross-quote alignment, terms matrix, scoring, and anti-hallucination currency rules."""

    def setUp(self):
        # Quote A: Atlas Piping Solutions
        item_a1 = LineItem(
            item_id="1",
            description="Seamless Steel Pipe 6 inch Class 300",
            quantity=100.0,
            unit_price=150.0,
            total_price=15000.0,
            currency=Currency.SAR,
        )
        item_a2 = LineItem(
            item_id="2",
            description="Flange Weld Neck 6 inch",
            quantity=20.0,
            unit_price=80.0,
            total_price=1600.0,
            currency=Currency.SAR,
        )
        terms_a = Terms(
            payment_terms="30% advance, 70% before delivery",
            delivery_lead_time_days=20,
            incoterm=Incoterm.DAP,
            named_place="Dammam Site",
            warranty_months=24,
            is_tax_included=False,
            is_shipping_included=True,
        )
        self.quote_a = Quotation(
            quote_id="Q-ATLAS-01",
            supplier_name="Atlas Piping Solutions FZE",
            currency=Currency.SAR,
            line_items=[item_a1, item_a2],
            subtotal=16600.0,
            total_amount=16600.0,
            terms=terms_a,
        )

        # Quote B: Gulf Heavy Industries (Cheaper pipes, faster delivery, but shorter warranty and no shipping included)
        item_b1 = LineItem(
            item_id="B-101",
            description="6-inch Seamless Steel Pipe Class 300",  # Wording variation
            quantity=100.0,
            unit_price=140.0,  # Cheaper!
            total_price=14000.0,
            currency=Currency.SAR,
        )
        item_b2 = LineItem(
            item_id="B-102",
            description="Flange Weld Neck 6 inch",
            quantity=20.0,
            unit_price=75.0,  # Cheaper!
            total_price=1500.0,
            currency=Currency.SAR,
        )
        terms_b = Terms(
            payment_terms="100% advance with order",
            delivery_lead_time_days=10,  # Faster!
            incoterm=Incoterm.EXW,
            named_place="Riyadh Factory",
            warranty_months=12,  # Shorter warranty
            is_tax_included=False,
            is_shipping_included=False,  # Excluded!
        )
        self.quote_b = Quotation(
            quote_id="Q-GULF-02",
            supplier_name="Gulf Heavy Industries Co.",
            currency=Currency.SAR,
            line_items=[item_b1, item_b2],
            subtotal=15500.0,
            total_amount=15500.0,
            terms=terms_b,
        )

    def test_token_similarity_helper(self):
        sim1 = token_similarity("Seamless Steel Pipe 6 inch", "6-inch Seamless Steel Pipe")
        self.assertGreaterEqual(sim1, 0.70)

        sim_diff = token_similarity("Industrial Centrifugal Pump", "Ball Valve 4-inch")
        self.assertEqual(sim_diff, 0.0)

    def test_compare_two_quotes_same_currency(self):
        comparator = QuotationComparator()
        report = comparator.compare([self.quote_a, self.quote_b])

        self.assertEqual(report.quotes_count, 2)
        self.assertEqual(len(report.item_comparisons), 2)

        # Verify pipe line item alignment
        pipe_comp = next(
            i for i in report.item_comparisons if "Pipe" in i.canonical_description
        )
        self.assertEqual(len(pipe_comp.matched_items), 2)
        self.assertEqual(pipe_comp.lowest_unit_price, 140.0)
        self.assertEqual(pipe_comp.lowest_price_supplier, "Gulf Heavy Industries Co.")
        self.assertAlmostEqual(pipe_comp.price_spread_percent, 7.14, delta=0.1)

        # Verify terms comparison
        self.assertEqual(report.terms_comparison.fastest_supplier, "Gulf Heavy Industries Co.")
        self.assertEqual(report.terms_comparison.longest_warranty_supplier, "Atlas Piping Solutions FZE")
        self.assertEqual(report.terms_comparison.delivery_lead_time_days["Gulf Heavy Industries Co."], 10)
        self.assertEqual(report.terms_comparison.delivery_lead_time_days["Atlas Piping Solutions FZE"], 20)

        # Verify lowest total cost supplier
        self.assertEqual(report.lowest_total_cost_supplier, "Gulf Heavy Industries Co.")

        # Verify Markdown table generation
        md_table = report.to_markdown_table()
        self.assertIn("Supplier Quotation Comparison Report", md_table)
        self.assertIn("Atlas Piping Solutions FZE", md_table)
        self.assertIn("Gulf Heavy Industries Co.", md_table)
        self.assertIn("Seamless Steel Pipe", md_table)

    def test_cross_currency_without_exchange_rate_preserves_currencies(self):
        # Quote C is in USD
        item_c = LineItem(
            item_id="C-1",
            description="Seamless Steel Pipe 6 inch",
            quantity=100.0,
            unit_price=40.0,
            total_price=4000.0,
            currency=Currency.USD,
        )
        quote_c = Quotation(
            quote_id="Q-USA-03",
            supplier_name="US Pipe Exports Inc",
            currency=Currency.USD,
            line_items=[item_c],
            total_amount=4000.0,
            terms=Terms(payment_terms="Net 30", delivery_lead_time_days=45),
        )

        comparator = QuotationComparator()  # No exchange rates passed
        report = comparator.compare([self.quote_a, quote_c])

        # Must flag in currency notes and not fabricate exchange rates
        self.assertTrue(len(report.currency_notes) > 0)
        self.assertIn("QuoteJudge strictly adheres to honest compliance", report.currency_notes[0])
        self.assertIn("native currencies without currency conversion", report.currency_notes[0])

        score_c = next(s for s in report.ranked_suppliers if s.supplier_name == "US Pipe Exports Inc")
        self.assertIsNone(score_c.normalized_total_amount)

    def test_cross_currency_with_explicit_rates_converts_accurately(self):
        item_c = LineItem(
            item_id="C-1",
            description="Seamless Steel Pipe 6 inch",
            quantity=100.0,
            unit_price=40.0,
            total_price=4000.0,
            currency=Currency.USD,
        )
        quote_c = Quotation(
            quote_id="Q-USA-03",
            supplier_name="US Pipe Exports Inc",
            currency=Currency.USD,
            line_items=[item_c],
            total_amount=4000.0,
            terms=Terms(payment_terms="Net 30", delivery_lead_time_days=45, warranty_months=12),
        )

        # Operator supplies explicit exchange rate: 1 USD = 3.75 SAR
        comparator = QuotationComparator(
            exchange_rates={"USD": 3.75, "SAR": 1.0},
            base_currency="SAR",
        )
        report = comparator.compare([self.quote_a, quote_c])

        score_c = next(s for s in report.ranked_suppliers if s.supplier_name == "US Pipe Exports Inc")
        # 4000 USD * 3.75 = 15000 SAR
        self.assertIsNotNone(score_c.normalized_total_amount)
        self.assertEqual(score_c.normalized_total_amount, 15000.0)

    def test_missing_terms_matrix_highlights_omissions(self):
        # Quote with completely empty terms
        item_d = LineItem(item_id="1", description="Spare Part", quantity=1.0, unit_price=10.0, total_price=10.0)
        incomplete_quote = Quotation(
            quote_id="Q-INCOMPLETE",
            supplier_name="Incomplete Supplier",
            currency=Currency.SAR,
            line_items=[item_d],
            total_amount=10.0,
            terms=Terms(),  # Empty!
        )

        comparator = QuotationComparator()
        report = comparator.compare([self.quote_a, incomplete_quote])

        alerts_d = report.missing_terms_matrix["Incomplete Supplier"]
        self.assertGreater(len(alerts_d), 4)

        # Markdown output must surface the missing terms
        md_text = report.to_markdown_table()
        self.assertIn("Incomplete Supplier", md_text)
        self.assertIn("Omitted Commercial Terms", md_text)

    def test_compare_empty_list_raises_value_error(self):
        comparator = QuotationComparator()
        with self.assertRaises(ValueError):
            comparator.compare([])


if __name__ == "__main__":
    unittest.main()
