"""Bilingual Clarification Generator for QuoteJudge.

Generates formal, grounded procurement clarification letters in English and Modern Standard Arabic
addressing missing terms, ambiguous specifications, unstated taxes, and delivery discrepancies.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Union

from .models import (
    Quotation,
    MissingTermAlert,
    MissingTermCategory,
)
from .comparator import ComparisonReport


@dataclass
class ClarificationQuestion:
    """Individual clarification item directed to a supplier."""
    category: str
    severity: str
    question_en: str
    question_ar: str
    context_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClarificationLetter:
    """Formal bilingual supplier clarification letter."""
    supplier_name: str
    quote_id: str
    quote_date: Optional[str]
    subject_en: str
    subject_ar: str
    body_en: str
    body_ar: str
    questions: List[ClarificationQuestion] = field(default_factory=list)
    has_critical_items: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supplier_name": self.supplier_name,
            "quote_id": self.quote_id,
            "quote_date": self.quote_date,
            "subject_en": self.subject_en,
            "subject_ar": self.subject_ar,
            "body_en": self.body_en,
            "body_ar": self.body_ar,
            "questions": [q.to_dict() for q in self.questions],
            "has_critical_items": self.has_critical_items,
        }

    def to_markdown(self, language: str = "bilingual") -> str:
        """Renders letter in Markdown format (bilingual, English-only, or Arabic-only)."""
        lines: List[str] = []
        lang = language.lower()

        if lang in ("bilingual", "en"):
            lines.append(f"# Commercial Clarification Request: {self.quote_id}\n")
            lines.append(f"**To:** {self.supplier_name}  ")
            lines.append(f"**Subject:** {self.subject_en}  ")
            if self.quote_date:
                lines.append(f"**Quotation Date:** {self.quote_date}  ")
            lines.append("\n" + self.body_en + "\n")

        if lang == "bilingual":
            lines.append("\n---\n")

        if lang in ("bilingual", "ar"):
            lines.append(f"# طلب استفسار تجاري بخصوص العرض رقم: {self.quote_id}\n")
            lines.append(f"**إلى:** {self.supplier_name}  ")
            lines.append(f"**الموضوع:** {self.subject_ar}  ")
            if self.quote_date:
                lines.append(f"**تاريخ العرض:** {self.quote_date}  ")
            lines.append("\n" + self.body_ar + "\n")

        return "\n".join(lines)


class BilingualClarificationGenerator:
    """Generates professional supplier clarification drafts grounded in missing terms and audit findings."""

    def __init__(
        self,
        buyer_company: str = "Commercial Procurement Department",
        contact_person: str = "Procurement Review Committee",
    ):
        self.buyer_company = buyer_company
        self.contact_person = contact_person

    def generate_letter(
        self,
        quote: Quotation,
        alerts: Optional[List[MissingTermAlert]] = None,
        custom_notes: Optional[List[str]] = None,
    ) -> ClarificationLetter:
        """Generates a formal bilingual clarification letter for a specific Quotation."""
        active_alerts = alerts if alerts is not None else quote.terms.detect_missing_terms()

        questions: List[ClarificationQuestion] = []
        has_crit = False

        for a in active_alerts:
            if a.severity in ("CRITICAL", "HIGH"):
                has_crit = True
            questions.append(
                ClarificationQuestion(
                    category=a.category.value,
                    severity=a.severity,
                    question_en=a.suggested_clarification_en,
                    question_ar=a.suggested_clarification_ar,
                    context_note=a.description_en,
                )
            )

        if custom_notes:
            for note in custom_notes:
                questions.append(
                    ClarificationQuestion(
                        category="COMMERCIAL_NOTE",
                        severity="MEDIUM",
                        question_en=f"Please clarify: {note}",
                        question_ar=f"يرجى التكرم بتوضيح: {note}",
                    )
                )

        # Subject lines
        subject_en = f"Commercial Clarification Request - Quotation Ref: {quote.quote_id}"
        subject_ar = f"طلب إيضاحات تجارية وفنية - عرض سعر رقم: {quote.quote_id}"

        # English Body Construction
        body_en = self._build_english_body(quote, questions)

        # Arabic Body Construction
        body_ar = self._build_arabic_body(quote, questions)

        return ClarificationLetter(
            supplier_name=quote.supplier_name,
            quote_id=quote.quote_id,
            quote_date=quote.quote_date,
            subject_en=subject_en,
            subject_ar=subject_ar,
            body_en=body_en,
            body_ar=body_ar,
            questions=questions,
            has_critical_items=has_crit,
        )

    def generate_letters_for_report(self, report: ComparisonReport) -> Dict[str, ClarificationLetter]:
        """Generates clarification letters for all suppliers with missing or ambiguous terms in a report."""
        letters: Dict[str, ClarificationLetter] = {}

        for s in report.ranked_suppliers:
            sup_name = s.supplier_name
            alerts = report.missing_terms_matrix.get(sup_name, [])
            if not alerts:
                continue

            # Find matching quotation metadata
            dummy_quote = Quotation(
                quote_id=s.quote_id,
                supplier_name=sup_name,
                currency=quote_currency_normalize(s.currency),
                total_amount=s.total_amount,
            )
            letters[sup_name] = self.generate_letter(dummy_quote, alerts=alerts)

        return letters

    def _build_english_body(self, quote: Quotation, questions: List[ClarificationQuestion]) -> str:
        lines: List[str] = []
        lines.append(f"Dear Sales & Commercial Team at {quote.supplier_name},\n")
        lines.append(
            f"Thank you for submitting your quotation (Reference: {quote.quote_id}) "
            f"for our procurement evaluation. We are currently reviewing all submitted proposals.\n"
        )

        if questions:
            lines.append("To ensure complete technical alignment and fair comparison, we kindly request your clarification on the following points:\n")
            for idx, q in enumerate(questions, 1):
                severity_tag = f"[{q.severity}] " if q.severity in ("CRITICAL", "HIGH") else ""
                lines.append(f"{idx}. {severity_tag}{q.question_en}")
                if q.context_note:
                    lines.append(f"   *Context*: {q.context_note}")
        else:
            lines.append("We confirm that all commercial and technical terms in your offer are clear and fully specified.\n")

        lines.append(
            "\nWe would appreciate receiving your written response and revised offer at your earliest convenience to proceed with final award evaluation.\n"
        )
        lines.append("Sincerely,\n")
        lines.append(f"**{self.contact_person}**  \n{self.buyer_company}")
        return "\n".join(lines)

    def _build_arabic_body(self, quote: Quotation, questions: List[ClarificationQuestion]) -> str:
        lines: List[str] = []
        lines.append(f"السادة / {quote.supplier_name} المحترمون،\n")
        lines.append("السلام عليكم ورحمة الله وبركاته،،،\n")
        lines.append(
            f"نشكركم على تقديم عرض السعر رقم ({quote.quote_id})، ونحيطكم علماً بأننا نقوم حالياً "
            f"بدراسة وتقييم العروض المقدمة لمشروعنا التجاري.\n"
        )

        if questions:
            lines.append("ولاستكمال متطلبات المقارنة الفنية والمالية بدقة، نرجو منكم التكرم بتوضيح النقاط الآتية:\n")
            for idx, q in enumerate(questions, 1):
                crit_prefix = "⚠️ [هام جداً] " if q.severity in ("CRITICAL", "HIGH") else ""
                lines.append(f"{idx}. {crit_prefix}{q.question_ar}")
        else:
            lines.append("نحيطكم علماً بأن جميع الشروط التجارية والفنية الواردة بعرضكم واضحة ومكتملة.\n")

        lines.append(
            "\nشاكرين ومقدرين حسن تعاونكم الدائم، ونتطلع إلى استلام ردكم الكريم وتحديث العرض في أقرب وقت لإتمام إجراءات الترسية.\n"
        )
        lines.append("وتفضلوا بقبول خالص التحية والتقدير،،،\n")
        lines.append(f"**{self.contact_person}**  \n{self.buyer_company}")
        return "\n".join(lines)


def quote_currency_normalize(curr: str):
    from .models import Currency
    return Currency.normalize(curr)
