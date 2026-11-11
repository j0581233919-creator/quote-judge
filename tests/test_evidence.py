"""Tests for QuoteJudge evidence extraction, offset tracking, and span verification."""

from __future__ import annotations
import unittest
from quote_judge.models import EvidenceSpan
from quote_judge.evidence import (
    calculate_line_number,
    extract_snippet_with_context,
    locate_evidence,
    locate_all_evidence,
    locate_evidence_regex,
    locate_all_evidence_regex,
    verify_evidence_span,
)


class TestEvidenceExtraction(unittest.TestCase):
    """Verifies precision offset calculations and source grounding."""

    def setUp(self):
        self.sample_text = (
            "Line 1: Supplier Quotation Header\n"
            "Line 2: Invoice No: INV-98765\n"
            "Line 3: Product: Stainless Steel Bolt M10\n"
            "Line 4: Qty: 500 pcs | Unit Price: 2.50 USD\n"
            "Line 5: Total: 1250.00 USD\n"
            "Line 6: Terms: 30 days net\n"
        )

    def test_calculate_line_number(self):
        self.assertEqual(calculate_line_number(self.sample_text, 0), 1)
        # Find start of Line 2
        line2_idx = self.sample_text.find("Line 2")
        self.assertEqual(calculate_line_number(self.sample_text, line2_idx), 2)
        # Find start of Line 5
        line5_idx = self.sample_text.find("Line 5")
        self.assertEqual(calculate_line_number(self.sample_text, line5_idx), 5)
        # Negative offset fallback
        self.assertEqual(calculate_line_number(self.sample_text, -10), 1)

    def test_extract_snippet_with_context(self):
        start = self.sample_text.find("INV-98765")
        end = start + len("INV-98765")
        snippet = extract_snippet_with_context(self.sample_text, start, end, context_chars=15)
        self.assertIn("INV-98765", snippet)
        self.assertTrue(snippet.startswith("..."))
        self.assertTrue(snippet.endswith("..."))

    def test_locate_evidence(self):
        target = "Stainless Steel Bolt M10"
        span = locate_evidence(self.sample_text, target, document_id="quote_doc_1", page_number=1)

        self.assertIsNotNone(span)
        self.assertEqual(span.exact_text, target)
        self.assertEqual(span.document_id, "quote_doc_1")
        self.assertEqual(span.page_number, 1)
        self.assertEqual(span.line_number, 3)

        # Verification against source text passes
        is_valid, err = verify_evidence_span(span, self.sample_text)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_locate_evidence_occurrence_indexing(self):
        repeat_text = "Apple Banana Apple Cherry Apple"
        # First occurrence (index 0)
        span0 = locate_evidence(repeat_text, "Apple", occurrence_index=0)
        self.assertIsNotNone(span0)
        self.assertEqual(span0.start_char, 0)

        # Last occurrence (index -1)
        span_last = locate_evidence(repeat_text, "Apple", occurrence_index=-1)
        self.assertIsNotNone(span_last)
        self.assertEqual(span_last.start_char, repeat_text.rfind("Apple"))

        # Second occurrence (index 1)
        span1 = locate_evidence(repeat_text, "Apple", occurrence_index=1)
        self.assertIsNotNone(span1)
        self.assertEqual(span1.start_char, 13)

        # Non-existent target
        self.assertIsNone(locate_evidence(repeat_text, "NonExistent"))

    def test_locate_all_evidence(self):
        text = "ITEM: Bolt QTY: 100\nITEM: Nut QTY: 200\nITEM: Washer QTY: 300\n"
        spans = locate_all_evidence(text, "ITEM:", document_id="doc_items")
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].line_number, 1)
        self.assertEqual(spans[1].line_number, 2)
        self.assertEqual(spans[2].line_number, 3)

        for s in spans:
            self.assertTrue(s.verify(text))

    def test_locate_evidence_regex(self):
        pattern = r"Unit Price:\s*(\d+\.\d+)\s*([A-Z]{3})"
        span = locate_evidence_regex(self.sample_text, pattern, document_id="doc_reg", group=1)
        self.assertIsNotNone(span)
        self.assertEqual(span.exact_text, "2.50")
        self.assertEqual(span.line_number, 4)
        self.assertTrue(span.verify(self.sample_text))

        span_curr = locate_evidence_regex(self.sample_text, pattern, document_id="doc_reg", group=2)
        self.assertIsNotNone(span_curr)
        self.assertEqual(span_curr.exact_text, "USD")
        self.assertEqual(span_curr.line_number, 4)
        self.assertTrue(span_curr.verify(self.sample_text))

    def test_locate_all_evidence_regex(self):
        text = "SKU-1001 price 50 USD, SKU-1002 price 75 USD, SKU-1003 price 120 USD"
        spans = locate_all_evidence_regex(text, r"SKU-(\d+)", group=0)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].exact_text, "SKU-1001")
        self.assertEqual(spans[1].exact_text, "SKU-1002")
        self.assertEqual(spans[2].exact_text, "SKU-1003")

    def test_verify_evidence_span_edge_cases(self):
        # Offset out of bounds
        out_of_bounds_span = EvidenceSpan(
            document_id="doc",
            start_char=500,
            end_char=510,
            exact_text="Out",
        )
        is_ok, err = verify_evidence_span(out_of_bounds_span, self.sample_text)
        self.assertFalse(is_ok)
        self.assertIn("Offset out of bounds", err)

        # Text mismatch
        mismatch_span = EvidenceSpan(
            document_id="doc",
            start_char=0,
            end_char=6,
            exact_text="Line X",  # actual text is "Line 1"
        )
        is_ok, err = verify_evidence_span(mismatch_span, self.sample_text)
        self.assertFalse(is_ok)
        self.assertIn("Evidence mismatch", err)


if __name__ == "__main__":
    unittest.main()
