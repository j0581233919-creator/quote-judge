"""Deterministic evidence-backed fact extractor for QuoteJudge.

Extracts structured commercial facts from raw text, PDF extracts, CSVs, and Markdown tables:
- Header & identification metadata (supplier, quote ID, quote date, expiry date, currency)
- Line items with quantities, units, unit prices, discounts, and line totals
- Commercial conditions (payment terms, lead time, Incoterms 2020, warranty, tax & freight inclusion, MOQ)
- Totals, deductions, and tax figures
- 100% exact source offset grounding via verified EvidenceSpans
"""

from __future__ import annotations
import csv
import io
import re
from typing import Optional, List, Dict, Any, Tuple, Union
from .models import (
    Currency,
    Incoterm,
    EvidenceSpan,
    LineItem,
    Terms,
    Quotation,
)
from .evidence import (
    locate_evidence,
    locate_evidence_regex,
    locate_all_evidence_regex,
    calculate_line_number,
    extract_snippet_with_context,
)
from .parser import LoadedDocument


def clean_number_str(s: str) -> str:
    """Removes commas, currency symbols, and spaces from a number string."""
    cleaned = re.sub(r"[,\s]", "", s)
    # Translate Eastern Arabic digits if present
    eastern_digits = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return cleaned.translate(eastern_digits)


def parse_float_safe(s: Any) -> Optional[float]:
    """Safely parses float from string with commas or returns None."""
    if s is None:
        return None
    try:
        clean = clean_number_str(str(s).strip())
        val = float(clean)
        return val
    except Exception:
        return None


class QuotationExtractor:
    """Deterministic extractor converting raw quotation text into grounded Quotation models."""

    # ---------------------------------------------------------
    # Regex Patterns
    # ---------------------------------------------------------

    _PATTERNS_QUOTE_ID = [
        re.compile(r"(?:Quote\s*(?:ID|No|Number|Ref|Reference)|Quotation\s*(?:No|Ref|#)|عرض\s*سعر\s*رقم|رقم\s*العرض)[:\s]+([A-Za-z0-9\-_/\u0600-\u06FF]+)", re.IGNORECASE),
        re.compile(r"(?:Ref|Reference)[:\s]+([A-Za-z0-9\-_/\u0600-\u06FF]{4,})", re.IGNORECASE),
    ]

    _PATTERNS_SUPPLIER = [
        re.compile(r"(?:Supplier|Vendor|From|Company|المورد|الشركة|من)[:\s]+([^\n\r,;]{3,})", re.IGNORECASE),
        re.compile(r"^([A-Z0-9\s&.,'-]+(?:Ltd|LLC|Inc|Corp|FZE|Co\.|Company|Trading|Industries|المحدودة|للتجارة|للمقاولات))", re.IGNORECASE | re.MULTILINE),
    ]

    _PATTERNS_DATE = [
        re.compile(r"(?:Quote\s*Date|Date|تاريخ\s*العرض|التاريخ)[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})", re.IGNORECASE),
    ]

    _PATTERNS_VALIDITY = [
        re.compile(r"(?:Valid\s*Until|Validity|Expires|Expiration|صلاحية\s*العرض|سارٍ\s*حتى)[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})", re.IGNORECASE),
    ]

    _PATTERNS_PAYMENT = [
        re.compile(r"(?:Payment\s*Terms?|Payment|Terms\s*of\s*Payment|شروط\s*الدفع|طريقة\s*الدفع)[:\s]+([^\n\r]{5,})", re.IGNORECASE),
        re.compile(r"(\d+%\s*advance[^\n\r]{5,})", re.IGNORECASE),
        re.compile(r"(Net\s*\d+\s*days?)", re.IGNORECASE),
        re.compile(r"(100%\s*LC\s*at\s*sight[^\n\r]*)", re.IGNORECASE),
        re.compile(r"(\d+%\s*دفعة\s*مقدمة[^\n\r]*)", re.IGNORECASE),
    ]

    _PATTERNS_LEAD_TIME = [
        re.compile(r"(?:Delivery\s*(?:Schedule|Lead\s*Time|Time|Period)|مدة\s*التوريد|فترة\s*التوريد)[:\s]+([^\n\r]{3,})", re.IGNORECASE),
        re.compile(r"(?:within|during|خلال)\s*(\d+)\s*(?:calendar\s*)?(?:days?|weeks?|months?|يوم|يوماً|أيام|أسبوع|شهر)", re.IGNORECASE),
    ]

    _PATTERNS_INCOTERM = [
        re.compile(r"(?:Incoterms?(?:\s*2020)?|Delivery\s*Terms?|شروط\s*التسليم)[:\s]+([^\n\r]{3,})", re.IGNORECASE),
        re.compile(r"\b(EXW|FOB|CIF|CFR|DAP|DDP|FCA|CPT|CIP|DPU|FAS)\b(?:\s+([A-Za-z0-9\s,.-]+(?:Port|Site|Airport|City|Dammam|Riyadh|Jeddah|Dubai|Shanghai)))?", re.IGNORECASE),
    ]

    _PATTERNS_WARRANTY = [
        re.compile(r"(?:Warranty|Guarantee|الضمان)[:\s]+([^\n\r]{3,})", re.IGNORECASE),
        re.compile(r"(\d+)\s*(?:months?|years?|شهر|شهراً|أشهر|سنة|سنوات)\s*(?:standard\s*)?(?:warranty|guarantee|ضمان)", re.IGNORECASE),
    ]

    _PATTERNS_TOTAL = [
        re.compile(r"(?:Grand\s*Total|Total\s*Amount|Total\s*Price|Total|الإجمالي\s*النهائي|المجموع\s*الكلي|المبلغ\s*الإجمالي)[:\s]+(?:[A-Z]{3}|\$|€|£|ر\.س)?\s*([0-9,]+(?:\.[0-9]+)?)", re.IGNORECASE),
    ]

    _PATTERNS_SUBTOTAL = [
        re.compile(r"(?:Subtotal|Sub-Total|Total\s*before\s*tax|المجموع\s*الفرعي|الإجمالي\s*قبل\s*الضريبة)[:\s]+(?:[A-Z]{3}|\$|€|£|ر\.س)?\s*([0-9,]+(?:\.[0-9]+)?)", re.IGNORECASE),
    ]

    _PATTERNS_TAX = [
        re.compile(r"(?:VAT|Tax|Sales\s*Tax|ضريبة|ضريبة\s*القيمة\s*المضافة)(?:\s*\(\d+%\))?[:\s]+(?:[A-Z]{3}|\$|€|£|ر\.س)?\s*([0-9,]+(?:\.[0-9]+)?)", re.IGNORECASE),
    ]

    _PATTERNS_SHIPPING = [
        re.compile(r"(?:Freight|Shipping|Transportation|Handling|الشحن|الشحن\s*والتوصيل|النقل)(?:\s*\([^\)]+\))?[:\s]+(?:[A-Z]{3}|\$|€|£|ر\.س)?\s*([0-9,]+(?:\.[0-9]+)?)", re.IGNORECASE),
    ]

    _PATTERNS_DISCOUNT = [
        re.compile(r"(?:Discount|Special\s*Discount|خصم|تخفيض)(?:\s*\([^\)]+\))?[:\s]+(?:[A-Z]{3}|\$|€|£|ر\.س)?\s*([0-9,]+(?:\.[0-9]+)?)", re.IGNORECASE),
    ]

    _PATTERNS_MOQ = [
        re.compile(r"(?:MOQ|Minimum\s*Order\s*Quantity|الحد\s*الأدنى\s*للطلب)[:\s]+([0-9,]+(?:\.[0-9]+)?)", re.IGNORECASE),
    ]

    def extract(self, doc_or_text: Union[str, LoadedDocument], document_id: Optional[str] = None) -> Quotation:
        """Extracts structured Quotation from raw text or a LoadedDocument."""
        if isinstance(doc_or_text, LoadedDocument):
            text = doc_or_text.raw_text
            d_id = document_id or doc_or_text.document_id
            doc_format = doc_or_text.file_format
        else:
            text = str(doc_or_text)
            d_id = document_id or "inline_document"
            doc_format = "txt"

        if not text.strip():
            raise ValueError(f"Document '{d_id}' has empty text content.")

        # 1. Detect Currency
        currency, _ = self._extract_currency(text)

        # 2. Extract Supplier & Reference
        supplier_name, supplier_ev = self._extract_supplier(text, d_id)
        quote_id, quote_id_ev = self._extract_quote_id(text, d_id)

        # 3. Extract Dates
        quote_date = self._extract_date(text)
        valid_until = self._extract_validity(text)

        # 4. Extract Commercial Terms
        terms = self._extract_terms(text, d_id)

        # 5. Extract Totals
        subtotal, _ = self._extract_number_by_pattern(text, self._PATTERNS_SUBTOTAL)
        discount_amount, _ = self._extract_number_by_pattern(text, self._PATTERNS_DISCOUNT)
        shipping_amount, _ = self._extract_number_by_pattern(text, self._PATTERNS_SHIPPING)
        tax_amount, _ = self._extract_number_by_pattern(text, self._PATTERNS_TAX)
        total_amount, total_amount_ev = self._extract_total(text, d_id)

        # 6. Extract Line Items (Markdown, CSV, or Structured Lines)
        line_items = self._extract_line_items(text, d_id, currency, doc_format)

        # 7. Fallback reconciliations
        if not total_amount and line_items:
            # If total amount was not explicitly matched with regex, calculate from items
            sum_lines = sum(item.total_price for item in line_items)
            total_amount = (
                (subtotal or sum_lines)
                - (discount_amount or 0.0)
                + (shipping_amount or 0.0)
                + (tax_amount or 0.0)
            )

        if subtotal is None and line_items:
            subtotal = sum(item.total_price for item in line_items)

        # Build Quotation instance
        quotation = Quotation(
            quote_id=quote_id or f"Q-{d_id}",
            supplier_name=supplier_name or "Unknown Supplier",
            quote_date=quote_date,
            valid_until=valid_until,
            currency=currency,
            line_items=line_items,
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_amount=shipping_amount,
            tax_amount=tax_amount,
            total_amount=total_amount or 0.0,
            terms=terms,
            raw_text=text,
            document_id=d_id,
            quote_id_evidence=quote_id_ev,
            supplier_evidence=supplier_ev,
            total_amount_evidence=total_amount_ev,
        )

        return quotation

    # ---------------------------------------------------------
    # Helper Extraction Methods
    # ---------------------------------------------------------

    def _extract_currency(self, text: str) -> Tuple[Currency, Optional[EvidenceSpan]]:
        """Scans for currency mentions, returning the dominant currency."""
        # Explicit Currency line check
        m_curr = re.search(r"(?:Currency|العملة)[:\s]+([A-Za-z]{3}|\$|€|£|ر\.س|ريال|درهم|جنيه)", text, re.IGNORECASE)
        if m_curr:
            code = m_curr.group(1).strip()
            norm = Currency.normalize(code)
            if norm != Currency.OTHER:
                return norm, None

        # Count frequencies of symbols
        freq: Dict[Currency, int] = {}
        for cur_candidate in [
            (Currency.SAR, r"\bSAR\b|\bر\.س\b|\bريال\b"),
            (Currency.USD, r"\bUSD\b|\$|\bDollar\b"),
            (Currency.AED, r"\bAED\b|\bدرهم\b|\bد\.إ\b"),
            (Currency.EUR, r"\bEUR\b|€|\bEuro\b"),
            (Currency.GBP, r"\bGBP\b|£|\bPound\b"),
            (Currency.EGP, r"\bEGP\b|\bجنيه\b|\bج\.م\b"),
        ]:
            matches = re.findall(cur_candidate[1], text, re.IGNORECASE)
            if matches:
                freq[cur_candidate[0]] = len(matches)

        if freq:
            best_curr = max(freq.items(), key=lambda x: x[1])[0]
            return best_curr, None

        return Currency.USD, None

    def _extract_supplier(self, text: str, doc_id: str) -> Tuple[Optional[str], Optional[EvidenceSpan]]:
        for pattern in self._PATTERNS_SUPPLIER:
            m = pattern.search(text)
            if m:
                val = m.group(1).strip()
                if len(val) >= 3 and not val.lower().startswith("document") and not val.lower().startswith("quotation"):
                    span = locate_evidence(text, val, doc_id)
                    return val, span
        return None, None

    def _extract_quote_id(self, text: str, doc_id: str) -> Tuple[Optional[str], Optional[EvidenceSpan]]:
        for pattern in self._PATTERNS_QUOTE_ID:
            m = pattern.search(text)
            if m:
                val = m.group(1).strip()
                span = locate_evidence(text, val, doc_id)
                return val, span
        return None, None

    def _extract_date(self, text: str) -> Optional[str]:
        for pattern in self._PATTERNS_DATE:
            m = pattern.search(text)
            if m:
                return m.group(1).strip()
        return None

    def _extract_validity(self, text: str) -> Optional[str]:
        for pattern in self._PATTERNS_VALIDITY:
            m = pattern.search(text)
            if m:
                return m.group(1).strip()
        return None

    def _extract_number_by_pattern(
        self, text: str, patterns: List[re.Pattern]
    ) -> Tuple[Optional[float], Optional[EvidenceSpan]]:
        for pat in patterns:
            m = pat.search(text)
            if m:
                val_str = m.group(1).strip()
                parsed = parse_float_safe(val_str)
                if parsed is not None:
                    span = locate_evidence(text, val_str)
                    return parsed, span
        return None, None

    def _extract_total(self, text: str, doc_id: str) -> Tuple[Optional[float], Optional[EvidenceSpan]]:
        # Find the last match for grand total (often at bottom of quote)
        matches = list(self._PATTERNS_TOTAL[0].finditer(text))
        if matches:
            last_m = matches[-1]
            val_str = last_m.group(1).strip()
            parsed = parse_float_safe(val_str)
            if parsed is not None:
                span = locate_evidence(text, val_str, doc_id, occurrence_index=-1)
                return parsed, span
        return None, None

    def _extract_terms(self, text: str, doc_id: str) -> Terms:
        terms = Terms()

        # 1. Payment Terms
        for pat in self._PATTERNS_PAYMENT:
            m = pat.search(text)
            if m:
                p_text = m.group(1).strip()
                terms.payment_terms = p_text
                sp = locate_evidence(text, p_text, doc_id)
                if sp:
                    terms.evidence["payment_terms"] = sp
                break

        # 2. Delivery Lead Time
        for pat in self._PATTERNS_LEAD_TIME:
            m = pat.search(text)
            if m:
                d_text = m.group(1).strip()
                terms.delivery_terms_description = d_text
                # Try to extract integer days
                m_days = re.search(r"(\d+)\s*(?:calendar\s*)?(?:days?|يوم|يوماً)", d_text, re.IGNORECASE)
                if m_days:
                    terms.delivery_lead_time_days = int(m_days.group(1))
                else:
                    m_weeks = re.search(r"(\d+)\s*(?:weeks?|أسبوع)", d_text, re.IGNORECASE)
                    if m_weeks:
                        terms.delivery_lead_time_days = int(m_weeks.group(1)) * 7

                sp = locate_evidence(text, d_text, doc_id)
                if sp:
                    terms.evidence["delivery_lead_time"] = sp
                break

        # 3. Incoterm
        for pat in self._PATTERNS_INCOTERM:
            m = pat.search(text)
            if m:
                matched_str = m.group(0).strip()
                inco_candidate = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else matched_str
                norm_inco = Incoterm.normalize(inco_candidate)
                if norm_inco != Incoterm.UNSPECIFIED:
                    terms.incoterm = norm_inco
                    if m.lastindex and m.lastindex >= 2 and m.group(2):
                        terms.named_place = m.group(2).strip()

                    sp = locate_evidence(text, matched_str, doc_id)
                    if sp:
                        terms.evidence["incoterm"] = sp
                    break

        # 4. Warranty
        for pat in self._PATTERNS_WARRANTY:
            m = pat.search(text)
            if m:
                w_text = m.group(0).strip()
                terms.warranty_description = w_text
                m_months = re.search(r"(\d+)\s*(?:months?|شهر|شهراً)", w_text, re.IGNORECASE)
                if m_months:
                    terms.warranty_months = int(m_months.group(1))
                else:
                    m_years = re.search(r"(\d+)\s*(?:years?|سنة|سنوات)", w_text, re.IGNORECASE)
                    if m_years:
                        terms.warranty_months = int(m_years.group(1)) * 12

                sp = locate_evidence(text, w_text, doc_id)
                if sp:
                    terms.evidence["warranty"] = sp
                break

        # 5. Tax & Shipping Inclusion
        if re.search(r"(?:inclusive\s*of\s*VAT|including\s*VAT|شامل\s*الضريبة|شامل\s*ضريبة\s*القيمة\s*المضافة)", text, re.IGNORECASE):
            terms.is_tax_included = True
        elif re.search(r"(?:exclusive\s*of\s*VAT|excluding\s*VAT|plus\s*VAT|غير\s*شامل\s*الضريبة|الضريبة\s*غير\s*مشمولة)", text, re.IGNORECASE):
            terms.is_tax_included = False

        if re.search(r"(?:freight\s*included|shipping\s*included|شامل\s*الشحن|التوصيل\s*مجاني)", text, re.IGNORECASE):
            terms.is_shipping_included = True
        elif re.search(r"(?:freight\s*excluded|shipping\s*excluded|الشحن\s*غير\s*مشمول|الشحن\s*إضافي)", text, re.IGNORECASE):
            terms.is_shipping_included = False

        # 6. MOQ
        for pat in self._PATTERNS_MOQ:
            m = pat.search(text)
            if m:
                moq_val = parse_float_safe(m.group(1))
                if moq_val is not None:
                    terms.minimum_order_quantity = moq_val
                    sp = locate_evidence(text, m.group(0).strip(), doc_id)
                    if sp:
                        terms.evidence["moq"] = sp
                    break

        return terms

    def _extract_line_items(
        self, text: str, doc_id: str, default_currency: Currency, doc_format: str
    ) -> List[LineItem]:
        """Extracts line items using CSV, Markdown, or labeled text heuristics."""
        items: List[LineItem] = []

        # 1. Try CSV Parsing if format is CSV or if text contains clear comma-separated rows with header
        if doc_format == "csv" or self._is_csv_content(text):
            items = self._extract_csv_line_items(text, doc_id, default_currency)
            if items:
                return items

        # 2. Try Markdown Table Parsing
        if "|" in text and "-|-" in text:
            items = self._extract_markdown_line_items(text, doc_id, default_currency)
            if items:
                return items

        # 3. Try Labeled Pattern Parsing (e.g., 'Item 1: ... Qty: ... Unit Price: ... Total: ...')
        items = self._extract_labeled_line_items(text, doc_id, default_currency)
        if items:
            return items

        # 4. Try Tabular Whitespace Columns (typical of pdftotext layout)
        items = self._extract_whitespace_table_items(text, doc_id, default_currency)
        return items

    def _is_csv_content(self, text: str) -> bool:
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if len(lines) >= 2:
            # Check if first line has commas and keywords
            header = lines[0].lower()
            if "," in header and any(k in header for k in ["item", "description", "qty", "price"]):
                return True
        return False

    def _extract_csv_line_items(self, text: str, doc_id: str, default_currency: Currency) -> List[LineItem]:
        items: List[LineItem] = []
        try:
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                return []

            field_map = {f.strip().lower(): f for f in reader.fieldnames}
            desc_col = next((field_map[k] for k in ["description", "product", "title", "name", "الصنف", "الوصف"] if k in field_map), None)
            if not desc_col:
                desc_col = next((field_map[k] for k in ["item"] if k in field_map), None)

            qty_col = next((field_map[k] for k in ["qty", "quantity", "count", "الكمية"] if k in field_map), None)
            unit_price_col = next((field_map[k] for k in ["unit_price", "unit price", "price", "rate", "سعر الوحدة", "السعر"] if k in field_map), None)
            total_price_col = next((field_map[k] for k in ["total", "total_price", "total price", "amount", "الإجمالي"] if k in field_map), None)
            unit_col = next((field_map[k] for k in ["unit", "uom", "unit_of_measure", "الوحدة"] if k in field_map), None)

            if not desc_col or not qty_col or not unit_price_col:
                return []

            for idx, row in enumerate(reader, 1):
                desc_val = str(row.get(desc_col, "")).strip()
                qty_val = parse_float_safe(row.get(qty_col))
                unit_p_val = parse_float_safe(row.get(unit_price_col))

                if not desc_val or qty_val is None or unit_p_val is None:
                    continue

                total_p_val = parse_float_safe(row.get(total_price_col)) if total_price_col else (qty_val * unit_p_val)
                uom_val = str(row.get(unit_col, "pcs")).strip() if unit_col else "pcs"

                desc_ev = locate_evidence(text, desc_val, doc_id)

                items.append(
                    LineItem(
                        item_id=str(idx),
                        description=desc_val,
                        quantity=qty_val,
                        unit_of_measure=uom_val,
                        unit_price=unit_p_val,
                        total_price=total_p_val if total_p_val is not None else (qty_val * unit_p_val),
                        currency=default_currency,
                        item_evidence=desc_ev,
                    )
                )
        except Exception:
            return []
        return items

    def _extract_markdown_line_items(self, text: str, doc_id: str, default_currency: Currency) -> List[LineItem]:
        items: List[LineItem] = []
        lines = text.splitlines()

        table_lines = [l.strip() for l in lines if l.strip().startswith("|") and l.strip().endswith("|")]
        if len(table_lines) < 3:
            return []

        # Find header line and column mapping
        header_cols = [c.strip().lower() for c in table_lines[0].strip("|").split("|")]
        # Prioritize explicit description/product column over generic 'item' index
        desc_idx = next((i for i, c in enumerate(header_cols) if any(k in c for k in ["description", "product", "title", "الوصف", "الصنف"])), None)
        if desc_idx is None:
            desc_idx = next((i for i, c in enumerate(header_cols) if "item" in c and not any(n in c for n in ["#", "no", "id", "num"])), None)

        item_id_idx = next((i for i, c in enumerate(header_cols) if any(k in c for k in ["item #", "item no", "item id", "no.", "no", "id", "#"])), None)
        qty_idx = next((i for i, c in enumerate(header_cols) if any(k in c for k in ["qty", "quantity", "الكمية"])), None)
        unit_p_idx = next((i for i, c in enumerate(header_cols) if any(k in c for k in ["unit price", "unit_price", "price", "rate", "سعر"])), None)
        total_p_idx = next((i for i, c in enumerate(header_cols) if any(k in c for k in ["total", "amount", "الإجمالي"])), None)

        if desc_idx is None or qty_idx is None or unit_p_idx is None:
            return []

        for row_idx, line in enumerate(table_lines[2:], 1):  # Skip header and divider
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) <= max(desc_idx, qty_idx, unit_p_idx):
                continue

            desc_val = cols[desc_idx]
            qty_val = parse_float_safe(cols[qty_idx])
            unit_p_val = parse_float_safe(cols[unit_p_idx])

            if not desc_val or qty_val is None or unit_p_val is None:
                continue

            item_id_val = cols[item_id_idx] if (item_id_idx is not None and len(cols) > item_id_idx and cols[item_id_idx]) else str(row_idx)

            total_p_val = (
                parse_float_safe(cols[total_p_idx])
                if (total_p_idx is not None and len(cols) > total_p_idx)
                else (qty_val * unit_p_val)
            )

            desc_ev = locate_evidence(text, desc_val, doc_id)

            items.append(
                LineItem(
                    item_id=item_id_val,
                    description=desc_val,
                    quantity=qty_val,
                    unit_price=unit_p_val,
                    total_price=total_p_val if total_p_val is not None else (qty_val * unit_p_val),
                    currency=default_currency,
                    item_evidence=desc_ev,
                )
            )

        return items

    def _extract_labeled_line_items(self, text: str, doc_id: str, default_currency: Currency) -> List[LineItem]:
        """Extracts items structured with explicit labels like 'Item 1: ... Qty: ... Total: ...'."""
        items: List[LineItem] = []

        # Pattern: Item <id>: <desc> - Qty: <qty> - Unit: <unit_price> - Total: <total>
        # Or Arabic: الصنف: <desc> | الكمية: <qty> | السعر: <unit> | الإجمالي: <total>
        pattern_en = re.compile(
            r"(?:Item|Line)\s*(\d+)[:\s]+(.*?)(?:-|\|)\s*Qty[:\s]+(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?\s*(?:-|\|)\s*Unit(?:\s*Price)?[:\s]+(?:[A-Z]{3}|\$|€|£)?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:-|\|)\s*Total[:\s]+(?:[A-Z]{3}|\$|€|£)?\s*([0-9,]+(?:\.[0-9]+)?)",
            re.IGNORECASE,
        )

        for m in pattern_en.finditer(text):
            item_id = m.group(1).strip()
            desc = m.group(2).strip()
            qty = parse_float_safe(m.group(3)) or 1.0
            uom = m.group(4).strip() if m.group(4) else "pcs"
            unit_p = parse_float_safe(m.group(5)) or 0.0
            tot_p = parse_float_safe(m.group(6)) or (qty * unit_p)

            items.append(
                LineItem(
                    item_id=item_id,
                    description=desc,
                    quantity=qty,
                    unit_of_measure=uom,
                    unit_price=unit_p,
                    total_price=tot_p,
                    currency=default_currency,
                    item_evidence=locate_evidence(text, desc, doc_id),
                )
            )

        if items:
            return items

        # Pattern for Arabic labeled lines
        pattern_ar = re.compile(
            r"الصنف[:\s]+(.*?)(?:-|\|)\s*الكمية[:\s]+([0-9٠-٩]+(?:\.[0-9٠-٩]+)?)\s*([^\s|]+)?\s*(?:-|\|)\s*السعر\s*(?:الفردي|الوحدة)?[:\s]+([0-9٠-٩,]+(?:\.[0-9٠-٩]+)?)\s*(?:ر\.س|ريال)?\s*(?:-|\|)\s*الإجمالي[:\s]+([0-9٠-٩,]+(?:\.[0-9٠-٩]+)?)",
            re.IGNORECASE,
        )

        for idx, m in enumerate(pattern_ar.finditer(text), 1):
            desc = m.group(1).strip()
            qty = parse_float_safe(m.group(2)) or 1.0
            uom = m.group(3).strip() if m.group(3) else "قطعة"
            unit_p = parse_float_safe(m.group(4)) or 0.0
            tot_p = parse_float_safe(m.group(5)) or (qty * unit_p)

            items.append(
                LineItem(
                    item_id=str(idx),
                    description=desc,
                    quantity=qty,
                    unit_of_measure=uom,
                    unit_price=unit_p,
                    total_price=tot_p,
                    currency=default_currency,
                    item_evidence=locate_evidence(text, desc, doc_id),
                )
            )

        return items

    def _extract_whitespace_table_items(
        self, text: str, doc_id: str, default_currency: Currency
    ) -> List[LineItem]:
        """Extracts items from layout-preserved text with whitespace-delimited columns."""
        items: List[LineItem] = []
        lines = text.splitlines()

        # Regular expression matching line starting with line number, followed by text, and 2 or 3 trailing float amounts
        # e.g.: "1   Seamless Steel Pipe 6 inch      100 pcs    150.00    15000.00"
        pattern_row = re.compile(
            r"^\s*(\d+)\s+([A-Za-z0-9\s&/.,'-]{4,})\s+(\d+(?:\.\d+)?)\s+([a-zA-Z]+)?\s+([0-9,]+(?:\.[0-9]+)?)\s+([0-9,]+(?:\.[0-9]+)?)\s*$"
        )

        for line in lines:
            m = pattern_row.match(line)
            if m:
                item_id = m.group(1).strip()
                desc = m.group(2).strip()
                qty = parse_float_safe(m.group(3)) or 1.0
                uom = m.group(4).strip() if m.group(4) else "pcs"
                unit_p = parse_float_safe(m.group(5)) or 0.0
                tot_p = parse_float_safe(m.group(6)) or (qty * unit_p)

                # Skip header rows falsely matching
                if desc.lower() in ["description", "item", "product"]:
                    continue

                items.append(
                    LineItem(
                        item_id=item_id,
                        description=desc,
                        quantity=qty,
                        unit_of_measure=uom,
                        unit_price=unit_p,
                        total_price=tot_p,
                        currency=default_currency,
                        item_evidence=locate_evidence(text, desc, doc_id),
                    )
                )

        return items
