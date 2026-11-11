# QuoteJudge Task Ledger

## Current Context
- **Current Task**: QJ-003 — Comparative Quotation Engine & Missing Terms Auditor.
- **Current Lifecycle State**: `READY`
- **Current Owner**: Gemini Flash (Lead Engineering Executor).
- **Branch**: main
- **Last Verified Commit**: f85ec80 (Milestone QJ-002 Certified ACCEPTED)
- **Independent Review Status**: ACCEPTED (Milestones QJ-001 and QJ-002 independently audited and certified ACCEPTED by EGM Goldfish Auditor; 35/35 tests passing)

## Backlog
| Task ID | Description | State | Owner | Acceptance Criteria |
|---------|-------------|-------|-------|---------------------|
| QJ-001  | Supplier Quotation Data Models & Evidence Extraction | **ACCEPTED** | Gemini Flash | 1. Typed schemas for `Quotation`, `LineItem`, `Terms`, `EvidenceSpan`, `Incoterm`, and `Currency`.<br>2. Exact source offset grounding (document, page, line, char start/end, text snippet).<br>3. Mathematical and logical consistency validation (unit price * qty vs total, subtotal + tax + shipping vs grand total).<br>4. Missing/unspecified terms detection (warranty, payment terms, validity, incoterms, tax inclusion, shipping inclusion).<br>5. Pure Python standard library with zero external dependencies.<br>6. Automated test suite passing with 0 failures.<br>7. Independent review by EGM Goldfish Auditor.<br>*Certified ACCEPTED by EGM Goldfish Auditor.* |
| QJ-002  | Text-based PDF & Structured Document Ingestion | **ACCEPTED** | Gemini Flash | 1. Multi-format ingestion engine (`quote_judge/parser.py`) supporting `.txt`, `.md`, `.csv`, `.json`, and text-based `.pdf` via `/usr/bin/pdftotext -layout`.<br>2. Fail-closed refusal for scanned or image-only PDFs (`OCRRequiredError`) with honest diagnostics.<br>3. Multi-encoding fallback (UTF-8, UTF-8-SIG, CP1256, Latin-1).<br>4. Deterministic fact extractor (`quote_judge/extractor.py`) across headers, line items, commercial conditions, and totals.<br>5. 100% exact source offset grounding for all extracted facts.<br>6. Automated consistency validation (`quote.validate()`).<br>7. Zero external PyPI dependencies.<br>8. Automated test suite passing with 0 failures (35/35 OK).<br>*Certified ACCEPTED by EGM Goldfish Auditor.* |
| QJ-003  | Comparative Quotation Engine & Missing Terms Auditor | READY | Pending | Side-by-side comparison, normalized unit evaluation, missing term alerts. |
| QJ-004  | Bilingual Clarification Generator & Export Formats | READY | Pending | Markdown/CSV exports and grounded AR/EN clarification drafts. |
| QJ-005  | CLI & End-to-End Verification Pipeline | READY | Pending | Behavioral test suite and end-to-end multi-supplier comparison demo. |

---

## Execution Receipts & Milestones
- **2026-11-10T01:42**: Canonical repository established at `/media/islam/shared pop/GitHub/quote-judge/repo`.
- **2026-11-11T02:17**: Governance policy updated; OpenAI Codex strictly disabled across repository; Google EGM Goldfish reviewers designated.
- **2026-11-11T03:10**: Milestone QJ-001 Implementation & Test Verification completed:
  - Implemented typed schemas in `quote_judge/models.py` (`Quotation`, `LineItem`, `Terms`, `EvidenceSpan`, `Currency`, `Incoterm`, `MissingTermAlert`, `QuotationValidationResult`).
  - Implemented source grounding engine in `quote_judge/evidence.py` (`locate_evidence`, `locate_all_evidence`, `locate_evidence_regex`, `verify_evidence_span`, `calculate_line_number`).
  - Implemented arithmetic integrity verification and missing commercial terms auditor with bilingual (AR/EN) clarification questions.
  - Added runnable interactive demonstration in `examples/run_demo.py`.
  - Added 20 automated tests across `test_models.py`, `test_evidence.py`, `test_arabic_quotes.py`.
  - Full test suite: **20/20 tests passing** (`python3 -m unittest discover tests`).
  - Commit: `a7ade85`.
  - Independent review receipt: EGM Goldfish Codebase Details Auditor (`egm-codebase-details` subagent `0c98ab2b-1697-47aa-8ffc-276edf98a2de`) delivered official **ACCEPTED** verdict recorded in `reviews/EGM_QJ001_ACCEPTANCE_VERDICT.md`.
  - QJ-001 lifecycle state: **ACCEPTED**.
- **2026-11-11T03:25**: Milestone QJ-002 Implementation & Test Verification completed:
  - Implemented `DocumentLoader` in `quote_judge/parser.py` supporting `.txt`, `.md`, `.csv`, `.json`, and text-based `.pdf` via `/usr/bin/pdftotext -layout`.
  - Implemented fail-closed scanned PDF guardrail (`OCRRequiredError`) with clear policy diagnostics.
  - Implemented `QuotationExtractor` in `quote_judge/extractor.py` handling CSV, Markdown tables, labeled text, and whitespace column tables.
  - Implemented 100% source offset grounding linking all facts to `EvidenceSpan` instances.
  - Added multi-format ingestion demonstration in `examples/run_ingestion_demo.py` covering all 5 operational scenarios.
  - Added 15 new unit and integration tests across `test_parser.py` and `test_extractor.py` including real system PDF generation via `ps2pdf`.
  - Full test suite: **35/35 tests passing** (`python3 -m unittest discover tests`).
  - Commit: `f85ec80`.
  - Independent review receipt: EGM Goldfish Codebase Details Auditor (`egm-codebase-details` subagent `5ae2e140-832d-4e61-9552-f9c70d588b85`) delivered official **ACCEPTED** verdict recorded in `reviews/EGM_QJ002_ACCEPTANCE_VERDICT.md`.
  - QJ-002 lifecycle state: **ACCEPTED**.

## Limitations & Notes
- Requires text-based PDF or structured text input; OCR capability is not simulated or assumed.
- EGM plugin status: not yet installed in host AGY CLI; will integrate fresh-context goldfish review upon installation approval.
