"""QuoteJudge: Evidence-backed supplier quotation comparison and missing terms auditor."""

__version__ = "1.0.0"

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

from .parser import (
    DocumentLoader,
    LoadedDocument,
    OCRRequiredError,
    UnsupportedFormatError,
)
from .extractor import QuotationExtractor

from .comparator import (
    QuotationComparator,
    ComparisonReport,
    ItemComparison,
    TermsComparison,
    SupplierScore,
    token_similarity,
)

from .clarification import (
    ClarificationQuestion,
    ClarificationLetter,
    BilingualClarificationGenerator,
)
from .export import (
    QuotationExporter,
    sanitize_csv_cell,
    desanitize_csv_cell,
    sanitize_csv_row,
    desanitize_csv_row,
)
from .demo import run_demo

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
    "DocumentLoader",
    "LoadedDocument",
    "OCRRequiredError",
    "UnsupportedFormatError",
    "QuotationExtractor",
    "QuotationComparator",
    "ComparisonReport",
    "ItemComparison",
    "TermsComparison",
    "SupplierScore",
    "token_similarity",
    "ClarificationQuestion",
    "ClarificationLetter",
    "BilingualClarificationGenerator",
    "QuotationExporter",
    "sanitize_csv_cell",
    "desanitize_csv_cell",
    "sanitize_csv_row",
    "desanitize_csv_row",
    "run_demo",
]
