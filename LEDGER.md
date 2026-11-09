# QuoteJudge Task Ledger

## Current Context
- **Current Task**: QJ-001 - Establish baseline specification, models, and text PDF quote parser.
- **Current Owner**: Unassigned (Scheduled after CatalogCopilot).
- **Branch**: main
- **Last Verified Commit**: None (Initial repository establishment)
- **Independent Review Status**: Not Started

## Backlog
| Task ID | Description | State | Owner | Acceptance Criteria |
|---------|-------------|-------|-------|---------------------|
| QJ-001  | Supplier Quotation Data Models & Evidence Extraction | READY | Pending | Typed schemas for Quotation, LineItem, Terms, and EvidenceSpan. |
| QJ-002  | Text-based PDF & Structured Document Ingestion | READY | Pending | Robust extraction of line items, currencies, Incoterms, and payment terms without OCR hallucination. |
| QJ-003  | Comparative Quotation Engine & Missing Terms Auditor | READY | Pending | Side-by-side comparison, normalized unit evaluation, missing term alerts. |
| QJ-004  | Bilingual Clarification Generator & Export Formats | READY | Pending | Markdown/CSV exports and grounded AR/EN clarification drafts. |
| QJ-005  | CLI & End-to-End Verification Pipeline | READY | Pending | Behavioral test suite and end-to-end multi-supplier comparison demo. |

## Limitations & Notes
- Requires text-based PDF or structured text input; OCR capability is not simulated or assumed.
- EGM plugin status: not yet installed in host AGY CLI; will integrate fresh-context goldfish review upon installation approval.
