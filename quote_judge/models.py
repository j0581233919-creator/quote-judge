"""Typed data models and evidence schemas for QuoteJudge.

Provides:
- EvidenceSpan: Source-grounded character and line offset representations.
- Currency and Incoterm enums with robust normalization.
- LineItem: Individual quotation items with arithmetic consistency validation.
- Terms: Commercial conditions with missing/ambiguous terms auditor.
- Quotation: Complete quotation document model with full integrity checks.
- QuotationValidationResult: Structured diagnostics for arithmetic, evidence, and terms.
"""

from __future__ import annotations
import math
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


class Currency(str, Enum):
    """Standard commercial transaction currencies."""
    USD = "USD"
    SAR = "SAR"
    AED = "AED"
    EUR = "EUR"
    GBP = "GBP"
    EGP = "EGP"
    CNY = "CNY"
    JPY = "JPY"
    KWD = "KWD"
    BHD = "BHD"
    OMR = "OMR"
    QAR = "QAR"
    TRY = "TRY"
    INR = "INR"
    OTHER = "OTHER"

    @classmethod
    def normalize(cls, val: Any) -> Currency:
        """Normalizes arbitrary string, code, or symbol into standard Currency."""
        if isinstance(val, Currency):
            return val
        if not val or not isinstance(val, str):
            return cls.OTHER
        s = val.strip().upper()
        if s in cls._value2member_map_:
            return cls(s)

        mapping = {
            "$": cls.USD,
            "US$": cls.USD,
            "DOLLAR": cls.USD,
            "DOLLARS": cls.USD,
            "ريال": cls.SAR,
            "ر.س": cls.SAR,
            "SR": cls.SAR,
            "ريال سعودي": cls.SAR,
            "درهم": cls.AED,
            "د.إ": cls.AED,
            "AED": cls.AED,
            "DIRHAM": cls.AED,
            "€": cls.EUR,
            "EURO": cls.EUR,
            "EUROS": cls.EUR,
            "£": cls.GBP,
            "POUND": cls.GBP,
            "POUNDS": cls.GBP,
            "STERLING": cls.GBP,
            "جنيه": cls.EGP,
            "ج.م": cls.EGP,
            "LE": cls.EGP,
            "EGP": cls.EGP,
            "¥": cls.CNY,
            "RMB": cls.CNY,
            "YUAN": cls.CNY,
            "YEN": cls.JPY,
            "KWD": cls.KWD,
            "د.ك": cls.KWD,
            "د.ب": cls.BHD,
            "BHD": cls.BHD,
            "ر.ع": cls.OMR,
            "OMR": cls.OMR,
            "ر.ق": cls.QAR,
            "QAR": cls.QAR,
        }
        return mapping.get(s, cls.OTHER)


class Incoterm(str, Enum):
    """ICC Incoterms 2020 rules for international commercial transactions."""
    EXW = "EXW"  # Ex Works
    FCA = "FCA"  # Free Carrier
    CPT = "CPT"  # Carriage Paid To
    CIP = "CIP"  # Carriage and Insurance Paid To
    DAP = "DAP"  # Delivered at Place
    DPU = "DPU"  # Delivered at Place Unloaded
    DDP = "DDP"  # Delivered Duty Paid
    FAS = "FAS"  # Free Alongside Ship
    FOB = "FOB"  # Free on Board
    CFR = "CFR"  # Cost and Freight
    CIF = "CIF"  # Cost, Insurance and Freight
    UNSPECIFIED = "UNSPECIFIED"

    @classmethod
    def normalize(cls, val: Any) -> Incoterm:
        """Normalizes string representation into standard Incoterm."""
        if isinstance(val, Incoterm):
            return val
        if not val or not isinstance(val, str):
            return cls.UNSPECIFIED
        s = val.strip().upper()
        if s in cls._value2member_map_:
            return cls(s)

        mapping = {
            "EX-WORKS": cls.EXW,
            "EX WORKS": cls.EXW,
            "FREE ON BOARD": cls.FOB,
            "COST AND FREIGHT": cls.CFR,
            "COST, INSURANCE AND FREIGHT": cls.CIF,
            "DELIVERED DUTY PAID": cls.DDP,
            "DELIVERED AT PLACE": cls.DAP,
            "FREE CARRIER": cls.FCA,
        }
        return mapping.get(s, cls.UNSPECIFIED)


class MissingTermCategory(str, Enum):
    """Categories of commercial terms analyzed for quotation completeness."""
    PAYMENT_TERMS = "PAYMENT_TERMS"
    DELIVERY_LEAD_TIME = "DELIVERY_LEAD_TIME"
    VALIDITY_PERIOD = "VALIDITY_PERIOD"
    INCOTERM = "INCOTERM"
    WARRANTY = "WARRANTY"
    TAX_INCLUSION = "TAX_INCLUSION"
    SHIPPING_INCLUSION = "SHIPPING_INCLUSION"
    MINIMUM_ORDER_QTY = "MINIMUM_ORDER_QTY"


@dataclass
class EvidenceSpan:
    """Represents verbatim source evidence linking extracted facts to exact text offsets."""
    document_id: str
    start_char: int
    end_char: int
    exact_text: str
    page_number: Optional[int] = None
    line_number: Optional[int] = None
    context: Optional[str] = None

    def __post_init__(self):
        self.document_id = str(self.document_id).strip()
        self.start_char = int(self.start_char)
        self.end_char = int(self.end_char)
        if self.start_char < 0 or self.end_char < self.start_char:
            raise ValueError(
                f"Invalid char offsets: start_char={self.start_char}, end_char={self.end_char}"
            )
        if self.page_number is not None:
            self.page_number = int(self.page_number)
            if self.page_number <= 0:
                raise ValueError(f"page_number must be 1-indexed (got {self.page_number})")
        if self.line_number is not None:
            self.line_number = int(self.line_number)
            if self.line_number <= 0:
                raise ValueError(f"line_number must be 1-indexed (got {self.line_number})")

    def verify(self, source_text: str) -> bool:
        """Verifies that the character offsets in source_text exactly match exact_text."""
        if self.start_char > len(source_text) or self.end_char > len(source_text):
            return False
        return source_text[self.start_char:self.end_char] == self.exact_text

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceSpan:
        return cls(
            document_id=data["document_id"],
            start_char=data["start_char"],
            end_char=data["end_char"],
            exact_text=data["exact_text"],
            page_number=data.get("page_number"),
            line_number=data.get("line_number"),
            context=data.get("context"),
        )


@dataclass
class MissingTermAlert:
    """Actionable alert detailing an absent or ambiguous quotation condition."""
    category: MissingTermCategory
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    description_en: str
    description_ar: str
    suggested_clarification_en: str
    suggested_clarification_ar: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MissingTermAlert:
        return cls(
            category=MissingTermCategory(data["category"]),
            severity=data.get("severity", "MEDIUM"),
            description_en=data["description_en"],
            description_ar=data["description_ar"],
            suggested_clarification_en=data["suggested_clarification_en"],
            suggested_clarification_ar=data["suggested_clarification_ar"],
        )


@dataclass
class LineItem:
    """Individual product or service quoted by the supplier."""
    item_id: str
    description: str
    quantity: float
    unit_of_measure: str = "pcs"
    unit_price: float = 0.0
    total_price: float = 0.0
    currency: Currency = Currency.USD
    discount: float = 0.0
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    item_evidence: Optional[EvidenceSpan] = None
    quantity_evidence: Optional[EvidenceSpan] = None
    unit_price_evidence: Optional[EvidenceSpan] = None
    total_price_evidence: Optional[EvidenceSpan] = None
    notes: Optional[str] = None

    def __post_init__(self):
        self.item_id = str(self.item_id).strip()
        self.description = str(self.description).strip()
        self.quantity = float(self.quantity)
        self.unit_of_measure = str(self.unit_of_measure).strip().lower()
        self.unit_price = float(self.unit_price)
        self.total_price = float(self.total_price)
        self.discount = float(self.discount)
        if not isinstance(self.currency, Currency):
            self.currency = Currency.normalize(self.currency)

        # Validate non-nan and non-negative
        for val_name, val in [
            ("quantity", self.quantity),
            ("unit_price", self.unit_price),
            ("total_price", self.total_price),
            ("discount", self.discount),
        ]:
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Line item '{self.item_id}' has non-finite {val_name}: {val}")
            if val < 0:
                raise ValueError(f"Line item '{self.item_id}' has negative {val_name}: {val}")

    def is_arithmetically_consistent(self, tolerance: float = 0.05) -> Tuple[bool, Optional[str]]:
        """Verifies that unit_price * quantity - discount matches total_price within tolerance."""
        expected_total = (self.quantity * self.unit_price) - self.discount
        diff = abs(expected_total - self.total_price)
        if diff <= tolerance:
            return True, None
        return (
            False,
            f"Arithmetic mismatch on item '{self.item_id}': {self.quantity} * {self.unit_price:.2f} "
            f"- {self.discount:.2f} = {expected_total:.2f}, but total_price is stated as {self.total_price:.2f} "
            f"(difference: {diff:.2f} {self.currency.value})",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "description": self.description,
            "quantity": self.quantity,
            "unit_of_measure": self.unit_of_measure,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "currency": self.currency.value,
            "discount": self.discount,
            "tax_rate": self.tax_rate,
            "tax_amount": self.tax_amount,
            "item_evidence": self.item_evidence.to_dict() if self.item_evidence else None,
            "quantity_evidence": self.quantity_evidence.to_dict() if self.quantity_evidence else None,
            "unit_price_evidence": self.unit_price_evidence.to_dict() if self.unit_price_evidence else None,
            "total_price_evidence": self.total_price_evidence.to_dict() if self.total_price_evidence else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineItem:
        return cls(
            item_id=data["item_id"],
            description=data["description"],
            quantity=data["quantity"],
            unit_of_measure=data.get("unit_of_measure", "pcs"),
            unit_price=data.get("unit_price", 0.0),
            total_price=data.get("total_price", 0.0),
            currency=Currency.normalize(data.get("currency", "USD")),
            discount=data.get("discount", 0.0),
            tax_rate=data.get("tax_rate"),
            tax_amount=data.get("tax_amount"),
            item_evidence=EvidenceSpan.from_dict(data["item_evidence"]) if data.get("item_evidence") else None,
            quantity_evidence=EvidenceSpan.from_dict(data["quantity_evidence"]) if data.get("quantity_evidence") else None,
            unit_price_evidence=EvidenceSpan.from_dict(data["unit_price_evidence"]) if data.get("unit_price_evidence") else None,
            total_price_evidence=EvidenceSpan.from_dict(data["total_price_evidence"]) if data.get("total_price_evidence") else None,
            notes=data.get("notes"),
        )


@dataclass
class Terms:
    """Commercial, legal, and operational terms accompanying a supplier quote."""
    payment_terms: Optional[str] = None
    delivery_lead_time_days: Optional[int] = None
    delivery_terms_description: Optional[str] = None
    valid_until: Optional[str] = None  # ISO date (YYYY-MM-DD)
    incoterm: Optional[Incoterm] = None
    named_place: Optional[str] = None
    warranty_months: Optional[int] = None
    warranty_description: Optional[str] = None
    is_tax_included: Optional[bool] = None  # None = unspecified
    tax_rate: Optional[float] = None
    is_shipping_included: Optional[bool] = None  # None = unspecified
    shipping_cost: Optional[float] = None
    minimum_order_quantity: Optional[float] = None
    evidence: Dict[str, EvidenceSpan] = field(default_factory=dict)

    def __post_init__(self):
        if self.incoterm is not None and not isinstance(self.incoterm, Incoterm):
            self.incoterm = Incoterm.normalize(self.incoterm)
        if self.delivery_lead_time_days is not None:
            self.delivery_lead_time_days = int(self.delivery_lead_time_days)
            if self.delivery_lead_time_days < 0:
                raise ValueError("delivery_lead_time_days cannot be negative")
        if self.warranty_months is not None:
            self.warranty_months = int(self.warranty_months)
            if self.warranty_months < 0:
                raise ValueError("warranty_months cannot be negative")

    def detect_missing_terms(self) -> List[MissingTermAlert]:
        """Detects absent or ambiguous commercial conditions that require clarification."""
        alerts: List[MissingTermAlert] = []

        # 1. Payment Terms
        if not self.payment_terms or not str(self.payment_terms).strip():
            alerts.append(
                MissingTermAlert(
                    category=MissingTermCategory.PAYMENT_TERMS,
                    severity="CRITICAL",
                    description_en="Quotation does not state payment conditions or payment milestones.",
                    description_ar="عرض السعر لا يوضح شروط أو مراحل الدفع.",
                    suggested_clarification_en="Could you please specify your required payment terms (e.g., advance percentage, LC, or credit period)?",
                    suggested_clarification_ar="يرجى التكرم بتحديد شروط الدفع المطلوبة (مثل نسبة الدفعة المقدمة، الاعتماد المستندي، أو فترة السداد).",
                )
            )

        # 2. Delivery Lead Time
        if self.delivery_lead_time_days is None and not self.delivery_terms_description:
            alerts.append(
                MissingTermAlert(
                    category=MissingTermCategory.DELIVERY_LEAD_TIME,
                    severity="HIGH",
                    description_en="Quotation does not specify delivery lead time or shipping schedule.",
                    description_ar="عرض السعر لا يحدد مدة التوريد أو الجدول الزمني للشحن.",
                    suggested_clarification_en="What is the expected delivery lead time upon order confirmation?",
                    suggested_clarification_ar="ما هي المدة المتوقعة للتوريد بعد تأكيد الطلب؟",
                )
            )

        # 3. Validity Period
        if not self.valid_until or not str(self.valid_until).strip():
            alerts.append(
                MissingTermAlert(
                    category=MissingTermCategory.VALIDITY_PERIOD,
                    severity="HIGH",
                    description_en="Quotation has no expiration date or validity period.",
                    description_ar="عرض السعر لا يتضمن تاريخ انتهاء أو فترة صلاحية محددة.",
                    suggested_clarification_en="Could you confirm the validity period for the quoted prices?",
                    suggested_clarification_ar="يرجى تأكيد فترة سريان وصلاحية الأسعار الموضحة بالعرض؟",
                )
            )

        # 4. Incoterms
        if self.incoterm is None or self.incoterm == Incoterm.UNSPECIFIED:
            alerts.append(
                MissingTermAlert(
                    category=MissingTermCategory.INCOTERM,
                    severity="HIGH",
                    description_en="Incoterms (delivery terms like EXW, FOB, CIF, DDP) are not specified.",
                    description_ar="لم يتم تحديد شروط التسليم الدولية (Incoterms مثل EXW أو FOB أو CIF أو DDP).",
                    suggested_clarification_en="Please clarify the agreed Incoterms 2020 and named destination or port of delivery.",
                    suggested_clarification_ar="يرجى توضيح شرط التسليم المعتمد (Incoterms 2020) والميناء أو مكان التسليم المحدد.",
                )
            )

        # 5. Warranty Terms
        if self.warranty_months is None and not self.warranty_description:
            alerts.append(
                MissingTermAlert(
                    category=MissingTermCategory.WARRANTY,
                    severity="MEDIUM",
                    description_en="Warranty period or after-sales support terms are not defined.",
                    description_ar="فترة الضمان وشروط الدعم الفني وخدمات ما بعد البيع غير موضحة.",
                    suggested_clarification_en="What warranty coverage or manufacturer guarantee is provided for these items?",
                    suggested_clarification_ar="ما هي فترة ونطاق الضمان المقدم لهذه الأصناف؟",
                )
            )

        # 6. Tax / VAT Inclusion
        if self.is_tax_included is None:
            alerts.append(
                MissingTermAlert(
                    category=MissingTermCategory.TAX_INCLUSION,
                    severity="HIGH",
                    description_en="It is not specified whether quoted prices are inclusive or exclusive of VAT/sales tax.",
                    description_ar="لم يتم توضيح ما إذا كانت الأسعار المعروضة شاملة أو غير شاملة لضريبة القيمة المضافة.",
                    suggested_clarification_en="Please clarify whether the stated prices include or exclude applicable VAT/taxes.",
                    suggested_clarification_ar="يرجى توضيح ما إذا كانت الأسعار تشمل أو تستثني ضريبة القيمة المضافة المقررة.",
                )
            )

        # 7. Shipping / Freight Inclusion
        if self.is_shipping_included is None and (self.incoterm in (Incoterm.EXW, Incoterm.FOB, Incoterm.FCA) or self.incoterm is None):
            alerts.append(
                MissingTermAlert(
                    category=MissingTermCategory.SHIPPING_INCLUSION,
                    severity="MEDIUM",
                    description_en="It is not specified whether shipping and transportation costs are included.",
                    description_ar="لم يتم توضيح ما إذا كانت تكاليف الشحن والنقل مشمولة في العرض أم إضافية.",
                    suggested_clarification_en="Are freight and domestic delivery charges included in the total price?",
                    suggested_clarification_ar="هل تكاليف الشحن والتوصيل الداخلي مشمولة في السعر الإجمالي؟",
                )
            )

        # 8. Minimum Order Quantity (MOQ)
        if self.minimum_order_quantity is None:
            alerts.append(
                MissingTermAlert(
                    category=MissingTermCategory.MINIMUM_ORDER_QTY,
                    severity="LOW",
                    description_en="Minimum Order Quantity (MOQ) is not indicated.",
                    description_ar="الحد الأدنى لكمية الطلب (MOQ) غير محدد.",
                    suggested_clarification_en="Is there a minimum order quantity (MOQ) or minimum order value required?",
                    suggested_clarification_ar="هل هناك حد أدنى للكمية أو القيمة المطلوبة للطلب؟",
                )
            )

        return alerts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_terms": self.payment_terms,
            "delivery_lead_time_days": self.delivery_lead_time_days,
            "delivery_terms_description": self.delivery_terms_description,
            "valid_until": self.valid_until,
            "incoterm": self.incoterm.value if self.incoterm else None,
            "named_place": self.named_place,
            "warranty_months": self.warranty_months,
            "warranty_description": self.warranty_description,
            "is_tax_included": self.is_tax_included,
            "tax_rate": self.tax_rate,
            "is_shipping_included": self.is_shipping_included,
            "shipping_cost": self.shipping_cost,
            "minimum_order_quantity": self.minimum_order_quantity,
            "evidence": {k: v.to_dict() for k, v in self.evidence.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Terms:
        incoterm_val = data.get("incoterm")
        evidence_dict = {
            k: EvidenceSpan.from_dict(v) for k, v in data.get("evidence", {}).items()
        }
        return cls(
            payment_terms=data.get("payment_terms"),
            delivery_lead_time_days=data.get("delivery_lead_time_days"),
            delivery_terms_description=data.get("delivery_terms_description"),
            valid_until=data.get("valid_until"),
            incoterm=Incoterm.normalize(incoterm_val) if incoterm_val else None,
            named_place=data.get("named_place"),
            warranty_months=data.get("warranty_months"),
            warranty_description=data.get("warranty_description"),
            is_tax_included=data.get("is_tax_included"),
            tax_rate=data.get("tax_rate"),
            is_shipping_included=data.get("is_shipping_included"),
            shipping_cost=data.get("shipping_cost"),
            minimum_order_quantity=data.get("minimum_order_quantity"),
            evidence=evidence_dict,
        )


@dataclass
class QuotationValidationResult:
    """Structured report detailing mathematical, evidentiary, and business validity."""
    is_valid: bool
    arithmetic_errors: List[str] = field(default_factory=list)
    evidence_errors: List[str] = field(default_factory=list)
    missing_term_alerts: List[MissingTermAlert] = field(default_factory=list)
    currency_mismatches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "arithmetic_errors": self.arithmetic_errors,
            "evidence_errors": self.evidence_errors,
            "missing_term_alerts": [a.to_dict() for a in self.missing_term_alerts],
            "currency_mismatches": self.currency_mismatches,
        }


@dataclass
class Quotation:
    """Complete supplier quotation document with evidence, terms, and items."""
    quote_id: str
    supplier_name: str
    quote_date: Optional[str] = None
    valid_until: Optional[str] = None
    currency: Currency = Currency.USD
    line_items: List[LineItem] = field(default_factory=list)
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    shipping_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total_amount: float = 0.0
    terms: Terms = field(default_factory=Terms)
    raw_text: Optional[str] = None
    document_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    quote_id_evidence: Optional[EvidenceSpan] = None
    supplier_evidence: Optional[EvidenceSpan] = None
    total_amount_evidence: Optional[EvidenceSpan] = None

    def __post_init__(self):
        self.quote_id = str(self.quote_id).strip()
        self.supplier_name = str(self.supplier_name).strip()
        if not self.quote_id:
            raise ValueError("Quotation must have a non-empty quote_id")
        if not self.supplier_name:
            raise ValueError("Quotation must have a non-empty supplier_name")

        if not isinstance(self.currency, Currency):
            self.currency = Currency.normalize(self.currency)

        self.total_amount = float(self.total_amount)
        if math.isnan(self.total_amount) or math.isinf(self.total_amount):
            raise ValueError(f"Quotation '{self.quote_id}' has non-finite total_amount: {self.total_amount}")
        if self.total_amount < 0:
            raise ValueError(f"Quotation '{self.quote_id}' has negative total_amount: {self.total_amount}")

        if self.subtotal is not None:
            self.subtotal = float(self.subtotal)
        if self.tax_amount is not None:
            self.tax_amount = float(self.tax_amount)
        if self.shipping_amount is not None:
            self.shipping_amount = float(self.shipping_amount)
        if self.discount_amount is not None:
            self.discount_amount = float(self.discount_amount)

    def validate(self, tolerance: float = 0.05, source_text: Optional[str] = None) -> QuotationValidationResult:
        """Validates arithmetic consistency, currency uniformity, source evidence, and missing terms."""
        arithmetic_errors: List[str] = []
        currency_mismatches: List[str] = []
        evidence_errors: List[str] = []

        # 1. Line-item arithmetic & currency uniformity
        sum_of_items = 0.0
        for item in self.line_items:
            sum_of_items += item.total_price

            # Item arithmetic
            ok_item, item_err = item.is_arithmetically_consistent(tolerance=tolerance)
            if not ok_item and item_err:
                arithmetic_errors.append(item_err)

            # Currency check
            if item.currency != self.currency and item.currency != Currency.OTHER:
                currency_mismatches.append(
                    f"Line item '{item.item_id}' currency '{item.currency.value}' differs from quote currency '{self.currency.value}'"
                )

        # 2. Subtotal check
        if self.subtotal is not None:
            diff_subtotal = abs(sum_of_items - self.subtotal)
            if diff_subtotal > tolerance:
                arithmetic_errors.append(
                    f"Subtotal mismatch: sum of line items is {sum_of_items:.2f} {self.currency.value}, "
                    f"but stated subtotal is {self.subtotal:.2f} {self.currency.value} (difference: {diff_subtotal:.2f})"
                )

        # 3. Grand total check
        base_subtotal = self.subtotal if self.subtotal is not None else sum_of_items
        calc_total = (
            base_subtotal
            - (self.discount_amount or 0.0)
            + (self.tax_amount or 0.0)
            + (self.shipping_amount or 0.0)
        )
        diff_total = abs(calc_total - self.total_amount)
        if diff_total > tolerance:
            arithmetic_errors.append(
                f"Total amount mismatch: calculated total is {calc_total:.2f} {self.currency.value} "
                f"(subtotal {base_subtotal:.2f} - discount {self.discount_amount or 0.0:.2f} + "
                f"tax {self.tax_amount or 0.0:.2f} + shipping {self.shipping_amount or 0.0:.2f}), "
                f"but stated total is {self.total_amount:.2f} {self.currency.value} (difference: {diff_total:.2f})"
            )

        # 4. Evidence verification (if source text available)
        txt = source_text or self.raw_text
        if txt:
            # Check quotation-level evidence
            for name, ev in [
                ("quote_id", self.quote_id_evidence),
                ("supplier_name", self.supplier_evidence),
                ("total_amount", self.total_amount_evidence),
            ]:
                if ev:
                    if not ev.verify(txt):
                        evidence_errors.append(
                            f"Quotation evidence verification failed for '{name}': offsets [{ev.start_char}:{ev.end_char}] "
                            f"do not match '{ev.exact_text}'"
                        )

            # Check line items evidence
            for item in self.line_items:
                for name, ev in [
                    (f"item '{item.item_id}' description", item.item_evidence),
                    (f"item '{item.item_id}' quantity", item.quantity_evidence),
                    (f"item '{item.item_id}' unit price", item.unit_price_evidence),
                    (f"item '{item.item_id}' total price", item.total_price_evidence),
                ]:
                    if ev and not ev.verify(txt):
                        evidence_errors.append(
                            f"Line item evidence verification failed for {name}: offsets [{ev.start_char}:{ev.end_char}] "
                            f"do not match '{ev.exact_text}'"
                        )

            # Check terms evidence
            for term_name, ev in self.terms.evidence.items():
                if ev and not ev.verify(txt):
                    evidence_errors.append(
                        f"Terms evidence verification failed for '{term_name}': offsets [{ev.start_char}:{ev.end_char}] "
                        f"do not match '{ev.exact_text}'"
                    )

        # 5. Missing terms audit
        missing_alerts = self.terms.detect_missing_terms()

        # Check overall validity: valid if zero arithmetic, zero evidence, and zero currency errors
        is_valid = len(arithmetic_errors) == 0 and len(evidence_errors) == 0 and len(currency_mismatches) == 0

        return QuotationValidationResult(
            is_valid=is_valid,
            arithmetic_errors=arithmetic_errors,
            evidence_errors=evidence_errors,
            missing_term_alerts=missing_alerts,
            currency_mismatches=currency_mismatches,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quote_id": self.quote_id,
            "supplier_name": self.supplier_name,
            "quote_date": self.quote_date,
            "valid_until": self.valid_until,
            "currency": self.currency.value,
            "line_items": [item.to_dict() for item in self.line_items],
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "shipping_amount": self.shipping_amount,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount,
            "terms": self.terms.to_dict(),
            "raw_text": self.raw_text,
            "document_id": self.document_id,
            "metadata": self.metadata,
            "quote_id_evidence": self.quote_id_evidence.to_dict() if self.quote_id_evidence else None,
            "supplier_evidence": self.supplier_evidence.to_dict() if self.supplier_evidence else None,
            "total_amount_evidence": self.total_amount_evidence.to_dict() if self.total_amount_evidence else None,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Quotation:
        items = [LineItem.from_dict(i) for i in data.get("line_items", [])]
        terms = Terms.from_dict(data["terms"]) if data.get("terms") else Terms()

        return cls(
            quote_id=data["quote_id"],
            supplier_name=data["supplier_name"],
            quote_date=data.get("quote_date"),
            valid_until=data.get("valid_until"),
            currency=Currency.normalize(data.get("currency", "USD")),
            line_items=items,
            subtotal=data.get("subtotal"),
            tax_amount=data.get("tax_amount"),
            shipping_amount=data.get("shipping_amount"),
            discount_amount=data.get("discount_amount"),
            total_amount=float(data.get("total_amount", 0.0)),
            terms=terms,
            raw_text=data.get("raw_text"),
            document_id=data.get("document_id"),
            metadata=data.get("metadata", {}),
            quote_id_evidence=EvidenceSpan.from_dict(data["quote_id_evidence"]) if data.get("quote_id_evidence") else None,
            supplier_evidence=EvidenceSpan.from_dict(data["supplier_evidence"]) if data.get("supplier_evidence") else None,
            total_amount_evidence=EvidenceSpan.from_dict(data["total_amount_evidence"]) if data.get("total_amount_evidence") else None,
        )

    @classmethod
    def from_json(cls, json_str: str) -> Quotation:
        return cls.from_dict(json.loads(json_str))
