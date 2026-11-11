# QuoteJudge Task Ledger

## Current Context
- **Current Task**: QJ-001 — Supplier Quotation Data Models & Evidence Extraction.
- **Current Lifecycle State**: `IN_PROGRESS`
- **Current Owner**: Gemini Flash (Lead Engineering Executor).
- **Branch**: main
- **Last Verified Commit**: bf7c0d8 (Baseline Governance Established)
- **Independent Review Status**: Not Started

## Backlog
| Task ID | Description | State | Owner | Acceptance Criteria |
|---------|-------------|-------|-------|---------------------|
| QJ-001  | Supplier Quotation Data Models & Evidence Extraction | IN_PROGRESS | Gemini Flash | 1. Typed schemas for `Quotation`, `LineItem`, `Terms`, `EvidenceSpan`, `Incoterm`, and `Currency`.<br>2. Exact source offset grounding (document, page, line, char start/end, text snippet).<br>3. Mathematical and logical consistency validation (unit price * qty vs total, subtotal + tax + shipping vs grand total).<br>4. Missing/unspecified terms detection (warranty, payment terms, validity, incoterms, tax inclusion, shipping inclusion).<br>5. Pure Python standard library with zero external dependencies.<br>6. Automated test suite passing with 0 failures.<br>7. Independent review by EGM Goldfish Auditor. |
| QJ-002  | Text-based PDF & Structured Document Ingestion | READY | Pending | Robust extraction of line items, currencies, Incoterms, and payment terms without OCR hallucination. |
| QJ-003  | Comparative Quotation Engine & Missing Terms Auditor | READY | Pending | Side-by-side comparison, normalized unit evaluation, missing term alerts. |
| QJ-004  | Bilingual Clarification Generator & Export Formats | READY | Pending | Markdown/CSV exports and grounded AR/EN clarification drafts. |
| QJ-005  | CLI & End-to-End Verification Pipeline | READY | Pending | Behavioral test suite and end-to-end multi-supplier comparison demo. |

## Limitations & Notes
- Requires text-based PDF or structured text input; OCR capability is not simulated or assumed.
- EGM plugin status: not yet installed in host AGY CLI; will integrate fresh-context goldfish review upon installation approval.
