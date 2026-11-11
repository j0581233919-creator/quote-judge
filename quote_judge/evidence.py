"""Evidence extraction, offset locating, and verification utilities for QuoteJudge.

Guarantees 100% source-grounded extraction:
- Exact character offsets (start_char, end_char)
- 1-indexed line numbering
- Surrounding context window generation
- Precise verbatim text verification against source documents
"""

from __future__ import annotations
import re
from typing import Optional, List, Tuple, Pattern, Union
from .models import EvidenceSpan


def calculate_line_number(text: str, char_offset: int) -> int:
    """Calculates 1-indexed line number corresponding to a 0-indexed character offset."""
    if char_offset < 0:
        return 1
    safe_offset = min(char_offset, len(text))
    return text.count("\n", 0, safe_offset) + 1


def extract_snippet_with_context(text: str, start: int, end: int, context_chars: int = 30) -> str:
    """Extracts text slice with surrounding context and ellipsis markers."""
    safe_start = max(0, start)
    safe_end = min(len(text), end)

    ctx_start = max(0, safe_start - context_chars)
    ctx_end = min(len(text), safe_end + context_chars)

    prefix = "..." if ctx_start > 0 else ""
    suffix = "..." if ctx_end < len(text) else ""

    return f"{prefix}{text[ctx_start:ctx_end].strip()}{suffix}"


def locate_evidence(
    text: str,
    target: str,
    document_id: str = "doc",
    page_number: Optional[int] = None,
    context_window: int = 40,
    occurrence_index: int = 0,
) -> Optional[EvidenceSpan]:
    """Locates target substring in text and constructs an EvidenceSpan.
    
    occurrence_index: 0 for the first occurrence, 1 for the second, or -1 for the last occurrence.
    """
    if not target or not text:
        return None

    if occurrence_index == 0:
        start_idx = text.find(target)
        if start_idx == -1:
            return None
    elif occurrence_index == -1:
        start_idx = text.rfind(target)
        if start_idx == -1:
            return None
    else:
        # Find all and pick the requested index
        all_spans = locate_all_evidence(
            text=text,
            target=target,
            document_id=document_id,
            page_number=page_number,
            context_window=context_window,
        )
        if 0 <= occurrence_index < len(all_spans):
            return all_spans[occurrence_index]
        return None

    end_idx = start_idx + len(target)
    line_no = calculate_line_number(text, start_idx)
    ctx = extract_snippet_with_context(text, start_idx, end_idx, context_chars=context_window)

    return EvidenceSpan(
        document_id=document_id,
        start_char=start_idx,
        end_char=end_idx,
        exact_text=target,
        page_number=page_number,
        line_number=line_no,
        context=ctx,
    )


def locate_all_evidence(
    text: str,
    target: str,
    document_id: str = "doc",
    page_number: Optional[int] = None,
    context_window: int = 40,
) -> List[EvidenceSpan]:
    """Finds all non-overlapping occurrences of target in text and returns EvidenceSpans."""
    if not target or not text:
        return []

    spans: List[EvidenceSpan] = []
    start_pos = 0
    t_len = len(target)

    while True:
        idx = text.find(target, start_pos)
        if idx == -1:
            break
        end_idx = idx + t_len
        line_no = calculate_line_number(text, idx)
        ctx = extract_snippet_with_context(text, idx, end_idx, context_chars=context_window)

        spans.append(
            EvidenceSpan(
                document_id=document_id,
                start_char=idx,
                end_char=end_idx,
                exact_text=target,
                page_number=page_number,
                line_number=line_no,
                context=ctx,
            )
        )
        start_pos = end_idx

    return spans


def locate_evidence_regex(
    text: str,
    pattern: Union[str, Pattern[str]],
    document_id: str = "doc",
    page_number: Optional[int] = None,
    group: int = 0,
    context_window: int = 40,
) -> Optional[EvidenceSpan]:
    """Locates the first match of regex pattern in text and returns an EvidenceSpan for the specified group."""
    if not text:
        return None

    compiled_pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
    match = compiled_pattern.search(text)
    if not match:
        return None

    start_idx, end_idx = match.span(group)
    exact_val = match.group(group)
    line_no = calculate_line_number(text, start_idx)
    ctx = extract_snippet_with_context(text, start_idx, end_idx, context_chars=context_window)

    return EvidenceSpan(
        document_id=document_id,
        start_char=start_idx,
        end_char=end_idx,
        exact_text=exact_val,
        page_number=page_number,
        line_number=line_no,
        context=ctx,
    )


def locate_all_evidence_regex(
    text: str,
    pattern: Union[str, Pattern[str]],
    document_id: str = "doc",
    page_number: Optional[int] = None,
    group: int = 0,
    context_window: int = 40,
) -> List[EvidenceSpan]:
    """Finds all regex matches in text and returns EvidenceSpans for the specified group."""
    if not text:
        return []

    compiled_pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
    spans: List[EvidenceSpan] = []

    for match in compiled_pattern.finditer(text):
        start_idx, end_idx = match.span(group)
        exact_val = match.group(group)
        line_no = calculate_line_number(text, start_idx)
        ctx = extract_snippet_with_context(text, start_idx, end_idx, context_chars=context_window)

        spans.append(
            EvidenceSpan(
                document_id=document_id,
                start_char=start_idx,
                end_char=end_idx,
                exact_text=exact_val,
                page_number=page_number,
                line_number=line_no,
                context=ctx,
            )
        )

    return spans


def verify_evidence_span(span: EvidenceSpan, source_text: str) -> Tuple[bool, Optional[str]]:
    """Verifies that an EvidenceSpan correctly aligns with source_text."""
    if span.start_char < 0:
        return False, f"Negative start_char offset: {span.start_char}"
    if span.end_char > len(source_text):
        return (
            False,
            f"Offset out of bounds: end_char {span.end_char} exceeds text length {len(source_text)}",
        )
    if span.start_char > span.end_char:
        return (
            False,
            f"Invalid offset range: start_char {span.start_char} > end_char {span.end_char}",
        )

    actual = source_text[span.start_char:span.end_char]
    if actual != span.exact_text:
        return (
            False,
            f"Evidence mismatch: expected exact text '{span.exact_text}', but found '{actual}' at offsets [{span.start_char}:{span.end_char}]",
        )

    return True, None
