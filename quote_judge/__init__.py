"""QuoteJudge: Evidence-backed supplier quotation comparison and missing terms auditor."""

__version__ = "0.1.0"

from .models import (
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
from .evidence import (
    locate_evidence,
    locate_all_evidence,
    locate_evidence_regex,
    locate_all_evidence_regex,
    calculate_line_number,
    extract_snippet_with_context,
    verify_evidence_span,
)

__all__ = [
    "Currency",
    "Incoterm",
    "MissingTermCategory",
    "MissingTermAlert",
    "EvidenceSpan",
    "LineItem",
    "Terms",
    "Quotation",
    "QuotationValidationResult",
    "locate_evidence",
    "locate_all_evidence",
    "locate_evidence_regex",
    "locate_all_evidence_regex",
    "calculate_line_number",
    "extract_snippet_with_context",
    "verify_evidence_span",
]
