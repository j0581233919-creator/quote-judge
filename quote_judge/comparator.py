"""Comparative Quotation Engine and Missing Terms Auditor for QuoteJudge.

Provides side-by-side supplier quote comparison:
- Cross-quote line item alignment and fuzzy product matching
- Unit price variance analysis and lowest-cost item identification
- Commercial conditions matrix (payment terms, lead times, Incoterms, warranties, freight, tax)
- Multi-currency handling with strict anti-hallucination policy (never invents exchange rates)
- Cross-supplier missing terms auditor and risk assessment
- Weighted multi-criteria decision matrix and ranking
- Markdown and dictionary report generation
"""

from __future__ import annotations
import math
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple, Set

from .models import (
    Currency,
    Incoterm,
    MissingTermCategory,
    MissingTermAlert,
    LineItem,
    Terms,
    Quotation,
)


def tokenize_product_name(s: str) -> Set[str]:
    """Extracts normalized alphanumeric and Arabic tokens from a product description."""
    cleaned = re.sub(r"[^\w\s\u0600-\u06FF]", " ", str(s).lower())
    tokens = {t for t in cleaned.split() if len(t) > 1 and t not in ("inch", "pcs", "mm", "قطعة", "متر")}
    return tokens


def token_similarity(s1: str, s2: str) -> float:
    """Computes Jaccard similarity over word tokens between two product descriptions."""
    t1 = tokenize_product_name(s1)
    t2 = tokenize_product_name(s2)
    if not t1 or not t2:
        return 0.0
    intersection = t1.intersection(t2)
    union = t1.union(t2)
    return len(intersection) / len(union)


@dataclass
class ItemComparison:
    """Side-by-side comparison of a single product line item across competing quotes."""
    canonical_description: str
    matched_items: Dict[str, LineItem] = field(default_factory=dict)  # supplier_name -> LineItem
    lowest_unit_price: float = 0.0
    lowest_price_supplier: str = ""
    highest_unit_price: float = 0.0
    highest_price_supplier: str = ""
    price_spread_percent: float = 0.0
    unit_of_measure: str = "pcs"
    currency: str = "USD"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_description": self.canonical_description,
            "matched_items": {k: v.to_dict() for k, v in self.matched_items.items()},
            "lowest_unit_price": self.lowest_unit_price,
            "lowest_price_supplier": self.lowest_price_supplier,
            "highest_unit_price": self.highest_unit_price,
            "highest_price_supplier": self.highest_price_supplier,
            "price_spread_percent": round(self.price_spread_percent, 2),
            "unit_of_measure": self.unit_of_measure,
            "currency": self.currency,
            "notes": self.notes,
        }


@dataclass
class TermsComparison:
    """Comparative matrix of commercial, delivery, and contractual conditions."""
    payment_terms: Dict[str, Optional[str]] = field(default_factory=dict)
    delivery_lead_time_days: Dict[str, Optional[int]] = field(default_factory=dict)
    fastest_supplier: Optional[str] = None
    incoterms: Dict[str, Optional[str]] = field(default_factory=dict)
    warranty_months: Dict[str, Optional[int]] = field(default_factory=dict)
    longest_warranty_supplier: Optional[str] = None
    is_tax_included: Dict[str, Optional[bool]] = field(default_factory=dict)
    is_shipping_included: Dict[str, Optional[bool]] = field(default_factory=dict)
    minimum_order_quantity: Dict[str, Optional[float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SupplierScore:
    """Multi-criteria evaluation score for a single supplier quote."""
    supplier_name: str
    quote_id: str
    total_amount: float
    currency: str
    normalized_total_amount: Optional[float]
    total_price_rank: int
    delivery_rank: int
    warranty_rank: int
    missing_critical_terms_count: int
    composite_score: float  # 0.0 to 100.0
    scoring_breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonReport:
    """Complete comparative analysis report across multiple supplier quotations."""
    quotes_count: int
    suppliers: List[str]
    currency_notes: List[str]
    item_comparisons: List[ItemComparison]
    terms_comparison: TermsComparison
    missing_terms_matrix: Dict[str, List[MissingTermAlert]]  # supplier_name -> list of alerts
    ranked_suppliers: List[SupplierScore]
    best_overall_supplier: Optional[str] = None
    lowest_total_cost_supplier: Optional[str] = None
    fastest_delivery_supplier: Optional[str] = None
    longest_warranty_supplier: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quotes_count": self.quotes_count,
            "suppliers": self.suppliers,
            "currency_notes": self.currency_notes,
            "item_comparisons": [i.to_dict() for i in self.item_comparisons],
            "terms_comparison": self.terms_comparison.to_dict(),
            "missing_terms_matrix": {
                k: [a.to_dict() for a in v] for k, v in self.missing_terms_matrix.items()
            },
            "ranked_suppliers": [s.to_dict() for s in self.ranked_suppliers],
            "best_overall_supplier": self.best_overall_supplier,
            "lowest_total_cost_supplier": self.lowest_total_cost_supplier,
            "fastest_delivery_supplier": self.fastest_delivery_supplier,
            "longest_warranty_supplier": self.longest_warranty_supplier,
        }

    def to_markdown_table(self) -> str:
        """Generates clean human-readable Markdown summary tables."""
        lines: List[str] = []
        lines.append(f"# Supplier Quotation Comparison Report ({self.quotes_count} Suppliers)\n")

        if self.currency_notes:
            for note in self.currency_notes:
                lines.append(f"> ⚠️ **Currency Notice**: {note}\n")

        # 1. Executive Summary Table
        lines.append("## 1. Executive Supplier Rankings\n")
        lines.append("| Rank | Supplier | Quote ID | Total Price | Lead Time | Warranty | Score / 100 |")
        lines.append("|:---:|:---|:---|:---:|:---:|:---:|:---:|")

        for idx, s in enumerate(self.ranked_suppliers, 1):
            lt_days = self.terms_comparison.delivery_lead_time_days.get(s.supplier_name)
            lt_str = f"{lt_days} days" if lt_days is not None else "Unspecified"
            w_m = self.terms_comparison.warranty_months.get(s.supplier_name)
            w_str = f"{w_m} mos" if w_m is not None else "Unspecified"
            price_str = f"{s.total_amount:,.2f} {s.currency}"
            if s.normalized_total_amount is not None and s.currency != "BASE":
                price_str += f" (~{s.normalized_total_amount:,.2f} BASE)"

            lines.append(
                f"| **{idx}** | **{s.supplier_name}** | {s.quote_id} | {price_str} | {lt_str} | {w_str} | **{s.composite_score:.1f}** |"
            )

        # 2. Line Item Price Comparison
        if self.item_comparisons:
            lines.append("\n## 2. Line-Item Unit Price Comparison\n")
            header = ["Product Description"] + [f"{s} (Unit Price)" for s in self.suppliers] + ["Lowest Supplier", "Spread"]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("|" + "|".join([":---" if i == 0 else ":---:" for i in range(len(header))]) + "|")

            for item_comp in self.item_comparisons:
                row = [item_comp.canonical_description]
                for sup in self.suppliers:
                    matched = item_comp.matched_items.get(sup)
                    if matched:
                        row.append(f"{matched.unit_price:,.2f} {matched.currency.value}")
                    else:
                        row.append("-")
                row.append(f"**{item_comp.lowest_price_supplier}**")
                row.append(f"{item_comp.price_spread_percent:.1f}%")
                lines.append("| " + " | ".join(row) + " |")

        # 3. Commercial Terms Side-by-Side
        lines.append("\n## 3. Commercial Terms Comparison\n")
        term_fields = [
            ("Payment Terms", self.terms_comparison.payment_terms),
            ("Delivery Lead Time", {k: f"{v} days" if v is not None else "None" for k, v in self.terms_comparison.delivery_lead_time_days.items()}),
            ("Incoterms 2020", self.terms_comparison.incoterms),
            ("Warranty Period", {k: f"{v} months" if v is not None else "None" for k, v in self.terms_comparison.warranty_months.items()}),
            ("VAT / Tax Included?", {k: "Yes" if v is True else ("No" if v is False else "Unspecified") for k, v in self.terms_comparison.is_tax_included.items()}),
            ("Shipping Included?", {k: "Yes" if v is True else ("No" if v is False else "Unspecified") for k, v in self.terms_comparison.is_shipping_included.items()}),
            ("MOQ", {k: str(v) if v is not None else "Unspecified" for k, v in self.terms_comparison.minimum_order_quantity.items()}),
        ]

        term_header = ["Condition"] + self.suppliers
        lines.append("| " + " | ".join(term_header) + " |")
        lines.append("|" + "|".join([":---" if i == 0 else ":---:" for i in range(len(term_header))]) + "|")

        for term_label, term_map in term_fields:
            row = [term_label]
            for sup in self.suppliers:
                row.append(str(term_map.get(sup) or "-"))
            lines.append("| " + " | ".join(row) + " |")

        # 4. Missing Terms Risk Audit
        lines.append("\n## 4. Omitted Commercial Terms & Risk Flags\n")
        has_any_missing = False
        for sup, alerts in self.missing_terms_matrix.items():
            if alerts:
                has_any_missing = True
                lines.append(f"### ⚠️ {sup} ({len(alerts)} Missing Terms):")
                for a in alerts:
                    lines.append(f"- **[{a.category.value}] ({a.severity})**: {a.description_en}")
                    lines.append(f"  *Suggested Clarification*: \"{a.suggested_clarification_en}\"")
                    lines.append(f"  *السؤال بالعربية*: \"{a.suggested_clarification_ar}\"")

        if not has_any_missing:
            lines.append("All participating suppliers provided complete and unambiguous commercial terms.")

        return "\n".join(lines)


class QuotationComparator:
    """Compares multiple supplier quotations, normalizes terms, and ranks proposals."""

    def __init__(
        self,
        price_weight: float = 0.50,
        delivery_weight: float = 0.25,
        warranty_weight: float = 0.15,
        completeness_weight: float = 0.10,
        exchange_rates: Optional[Dict[str, float]] = None,
        base_currency: str = "SAR",
    ):
        """Initializes comparator with configurable multi-criteria scoring weights.
        
        exchange_rates: mapping of currency code -> rate to base_currency (e.g. {"USD": 3.75, "SAR": 1.0}).
        QuoteJudge strictly avoids fabricating live rates; exchange rates must be explicitly passed.
        """
        total_w = price_weight + delivery_weight + warranty_weight + completeness_weight
        if abs(total_w - 1.0) > 0.01:
            # Normalize weights to sum to 1.0
            self.price_weight = price_weight / total_w
            self.delivery_weight = delivery_weight / total_w
            self.warranty_weight = warranty_weight / total_w
            self.completeness_weight = completeness_weight / total_w
        else:
            self.price_weight = price_weight
            self.delivery_weight = delivery_weight
            self.warranty_weight = warranty_weight
            self.completeness_weight = completeness_weight

        self.exchange_rates = {k.upper(): float(v) for k, v in (exchange_rates or {}).items()}
        self.base_currency = base_currency.upper()

    def compare(self, quotes: List[Quotation]) -> ComparisonReport:
        """Executes full comparative analysis across a list of Quotations."""
        if not quotes:
            raise ValueError("QuotationComparator requires at least one Quotation to analyze.")

        suppliers = [q.supplier_name for q in quotes]
        currency_notes: List[str] = []

        # 1. Multi-Currency Analysis
        currencies_present = {q.currency.value for q in quotes}
        can_convert = False
        if len(currencies_present) > 1:
            # Cross-currency situation
            missing_rates = [c for c in currencies_present if c != self.base_currency and c not in self.exchange_rates]
            if missing_rates:
                currency_notes.append(
                    f"Quotations use multiple currencies ({', '.join(currencies_present)}). "
                    f"Exchange rates were not provided for: {', '.join(missing_rates)}. "
                    f"QuoteJudge strictly adheres to honest compliance: financial rankings reflect native currencies without currency conversion."
                )
                can_convert = False
            else:
                can_convert = True
                currency_notes.append(
                    f"Converted cross-currency totals to base currency '{self.base_currency}' "
                    f"using explicit rates: {', '.join(f'1 {k}={v} {self.base_currency}' for k, v in self.exchange_rates.items())}."
                )

        # 2. Line-Item Alignment across Quotes
        item_comparisons = self._align_line_items(quotes)

        # 3. Commercial Terms Comparison
        terms_comp = self._compare_terms(quotes)

        # 4. Missing Terms Audit
        missing_terms_matrix = {
            q.supplier_name: q.terms.detect_missing_terms() for q in quotes
        }

        # 5. Calculate Normalized Totals & Supplier Scores
        ranked_suppliers = self._score_and_rank_suppliers(
            quotes=quotes,
            can_convert=can_convert,
            missing_terms_matrix=missing_terms_matrix,
        )

        # 6. Highlights
        best_overall = ranked_suppliers[0].supplier_name if ranked_suppliers else None
        lowest_cost_sup = min(ranked_suppliers, key=lambda s: (s.normalized_total_amount if s.normalized_total_amount is not None else s.total_amount)).supplier_name if ranked_suppliers else None

        return ComparisonReport(
            quotes_count=len(quotes),
            suppliers=suppliers,
            currency_notes=currency_notes,
            item_comparisons=item_comparisons,
            terms_comparison=terms_comp,
            missing_terms_matrix=missing_terms_matrix,
            ranked_suppliers=ranked_suppliers,
            best_overall_supplier=best_overall,
            lowest_total_cost_supplier=lowest_cost_sup,
            fastest_delivery_supplier=terms_comp.fastest_supplier,
            longest_warranty_supplier=terms_comp.longest_warranty_supplier,
        )

    def _align_line_items(self, quotes: List[Quotation]) -> List[ItemComparison]:
        """Aligns line items across quotes using exact SKU or token similarity."""
        comparisons: List[ItemComparison] = []
        all_items: List[Tuple[str, LineItem]] = []  # (supplier_name, item)

        for q in quotes:
            for item in q.line_items:
                all_items.append((q.supplier_name, item))

        visited_items: Set[Tuple[str, str]] = set()  # (supplier_name, item_id)

        for sup, item in all_items:
            key = (sup, item.item_id)
            if key in visited_items:
                continue

            # Start a new item cluster
            matched: Dict[str, LineItem] = {sup: item}
            visited_items.add(key)

            # Search for matching items in other quotes
            for other_sup, other_item in all_items:
                other_key = (other_sup, other_item.item_id)
                if other_key in visited_items or other_sup in matched:
                    continue

                # Compare description similarity
                sim = token_similarity(item.description, other_item.description)
                if sim >= 0.50 or (item.description.lower() in other_item.description.lower()) or (other_item.description.lower() in item.description.lower()):
                    matched[other_sup] = other_item
                    visited_items.add(other_key)

            # Calculate price spread and lowest unit price
            unit_prices = [it.unit_price for it in matched.values()]
            lowest_price = min(unit_prices)
            highest_price = max(unit_prices)
            spread = ((highest_price - lowest_price) / lowest_price * 100.0) if lowest_price > 0 else 0.0

            lowest_sup = next(s for s, it in matched.items() if it.unit_price == lowest_price)
            highest_sup = next(s for s, it in matched.items() if it.unit_price == highest_price)

            comparisons.append(
                ItemComparison(
                    canonical_description=item.description,
                    matched_items=matched,
                    lowest_unit_price=lowest_price,
                    lowest_price_supplier=lowest_sup,
                    highest_unit_price=highest_price,
                    highest_price_supplier=highest_sup,
                    price_spread_percent=spread,
                    unit_of_measure=item.unit_of_measure,
                    currency=item.currency.value,
                )
            )

        return comparisons

    def _compare_terms(self, quotes: List[Quotation]) -> TermsComparison:
        """Constructs comparative matrix of commercial conditions."""
        tc = TermsComparison()

        for q in quotes:
            sup = q.supplier_name
            t = q.terms
            tc.payment_terms[sup] = t.payment_terms
            tc.delivery_lead_time_days[sup] = t.delivery_lead_time_days
            tc.incoterms[sup] = f"{t.incoterm.value} {t.named_place or ''}".strip() if t.incoterm else None
            tc.warranty_months[sup] = t.warranty_months
            tc.is_tax_included[sup] = t.is_tax_included
            tc.is_shipping_included[sup] = t.is_shipping_included
            tc.minimum_order_quantity[sup] = t.minimum_order_quantity

        # Determine fastest supplier
        valid_lead_times = {s: d for s, d in tc.delivery_lead_time_days.items() if d is not None}
        if valid_lead_times:
            tc.fastest_supplier = min(valid_lead_times.items(), key=lambda x: x[1])[0]

        # Determine longest warranty supplier
        valid_warranties = {s: w for s, w in tc.warranty_months.items() if w is not None}
        if valid_warranties:
            tc.longest_warranty_supplier = max(valid_warranties.items(), key=lambda x: x[1])[0]

        return tc

    def _score_and_rank_suppliers(
        self,
        quotes: List[Quotation],
        can_convert: bool,
        missing_terms_matrix: Dict[str, List[MissingTermAlert]],
    ) -> List[SupplierScore]:
        """Calculates multi-criteria normalized scores (0 to 100) and ranks suppliers."""
        scores: List[SupplierScore] = []

        # 1. Determine effective comparison price
        norm_totals: Dict[str, Optional[float]] = {}
        for q in quotes:
            if can_convert:
                curr_str = q.currency.value
                if curr_str == self.base_currency:
                    norm_totals[q.supplier_name] = q.total_amount
                else:
                    rate = self.exchange_rates.get(curr_str, 1.0)
                    norm_totals[q.supplier_name] = q.total_amount * rate
            else:
                norm_totals[q.supplier_name] = None

        # Min and Max price for score normalization
        prices_for_scoring = [
            norm_totals[q.supplier_name] if norm_totals[q.supplier_name] is not None else q.total_amount
            for q in quotes
        ]
        min_p = min(prices_for_scoring)
        max_p = max(prices_for_scoring)

        # Lead times
        lead_times = [
            q.terms.delivery_lead_time_days
            for q in quotes
            if q.terms.delivery_lead_time_days is not None
        ]
        min_lt = min(lead_times) if lead_times else 1
        max_lt = max(lead_times) if lead_times else 30

        # Warranties
        warranties = [
            q.terms.warranty_months
            for q in quotes
            if q.terms.warranty_months is not None
        ]
        min_w = min(warranties) if warranties else 0
        max_w = max(warranties) if warranties else 24

        for q in quotes:
            sup = q.supplier_name
            p_val = norm_totals[sup] if norm_totals[sup] is not None else q.total_amount

            # Price Score: cheaper is better (100 = cheapest)
            if max_p == min_p:
                price_score = 100.0
            else:
                price_score = max(0.0, 100.0 - ((p_val - min_p) / (max_p - min_p) * 100.0))

            # Delivery Score: shorter is better (100 = fastest)
            lt = q.terms.delivery_lead_time_days
            if lt is None:
                delivery_score = 40.0  # Penalty for unspecified delivery time
            elif max_lt == min_lt:
                delivery_score = 100.0
            else:
                delivery_score = max(0.0, 100.0 - ((lt - min_lt) / (max_lt - min_lt) * 100.0))

            # Warranty Score: longer is better (100 = longest)
            wm = q.terms.warranty_months
            if wm is None:
                warranty_score = 20.0  # Penalty for missing warranty
            elif max_w == min_w:
                warranty_score = 100.0
            else:
                warranty_score = (wm / max_w) * 100.0 if max_w > 0 else 50.0

            # Completeness Score: penalize missing terms
            alerts = missing_terms_matrix.get(sup, [])
            crit_count = sum(1 for a in alerts if a.severity in ("CRITICAL", "HIGH"))
            completeness_score = max(0.0, 100.0 - (crit_count * 20.0))

            composite = (
                (price_score * self.price_weight)
                + (delivery_score * self.delivery_weight)
                + (warranty_score * self.warranty_weight)
                + (completeness_score * self.completeness_weight)
            )

            scores.append(
                SupplierScore(
                    supplier_name=sup,
                    quote_id=q.quote_id,
                    total_amount=q.total_amount,
                    currency=q.currency.value,
                    normalized_total_amount=norm_totals[sup],
                    total_price_rank=0,  # Will assign below
                    delivery_rank=0,
                    warranty_rank=0,
                    missing_critical_terms_count=crit_count,
                    composite_score=round(composite, 2),
                    scoring_breakdown={
                        "price_score": round(price_score, 1),
                        "delivery_score": round(delivery_score, 1),
                        "warranty_score": round(warranty_score, 1),
                        "completeness_score": round(completeness_score, 1),
                    },
                )
            )

        # Sort and assign ranks
        scores.sort(key=lambda s: s.composite_score, reverse=True)

        # Assign total price ranks
        sorted_by_price = sorted(scores, key=lambda s: s.normalized_total_amount if s.normalized_total_amount is not None else s.total_amount)
        for rank, s in enumerate(sorted_by_price, 1):
            s.total_price_rank = rank

        return scores
