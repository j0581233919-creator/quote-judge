# AGENTS.md — QuoteJudge

## Authority & Mission
QuoteJudge is an evidence-backed supplier quotation comparison system designed to ingest text-based supplier quotations (e.g., PDF/text), extract structured prices, quantities, terms, and units with exact source grounding, identify missing or conflicting terms, compare competing quotes side-by-side, and produce bilingual clarification questions.

## Core Rules & Guardrails
1. **Source Grounding**: Every extracted fact (unit price, total price, currency, payment terms, delivery lead time, MOQ, Incoterms) must be linked to exact source evidence (page, bounding/text offset, or excerpt).
2. **No Hallucinated OCR or Exchange Rates**: Never invent OCR text or fabricate exchange rates. If a currency conversion is required, state the explicit conversion rate used or preserve quotes in original currencies with comparison notes.
3. **Missing Terms Detection**: Explicitly detect and highlight missing terms (e.g., warranty, shipping fees, tax/VAT inclusion, validity period).
4. **Side-by-Side Comparison**: Generate structured tabular comparison and clear exportable summaries (JSON, CSV, Markdown).
5. **Bilingual Clarification**: Formulate clear supplier clarification inquiries in Arabic and English for missing or ambiguous terms.
6. **Independent Review Requirement & Codex Exclusion Policy**:
   - OpenAI Codex CLI and API are **strictly disabled** for this development program (CatalogCopilot, QuoteJudge, BayanGate).
   - Never invoke Codex directly or indirectly (via CLI, AGY, Mezo, Hermes, MezoExecutor, EGM, or fallback loops).
   - Independent engineering review and certification are conducted via verified Google Elephant-Goldfish Model (EGM) Goldfish reviewers (`egm-codebase-details` and `egm-structural`) using genuine fresh-context subagents.
   - Flash/Executor agents must NOT certify their own implementation as independently reviewed.

## Lifecycle States
`READY` -> `IN_PROGRESS` -> `IMPLEMENTED` -> `TESTED` -> `REVIEW_PENDING` -> `ACCEPTED` -> `RELEASE_READY`

## Task Ledger Summary
- **Current Task**: QJ-002 — Text-based PDF & Structured Document Ingestion.
- **Current Lifecycle State**: `IN_PROGRESS`
- **Current Owner**: Gemini Flash (Lead Engineering Executor).
- **Independent Reviewer**: EGM Goldfish Codebase Details Auditor (`egm-codebase-details`).
- **Branch**: main
- **Last Verified Commit**: a40cd16
- **Independent Review Status**: Milestone QJ-001 Certified ACCEPTED; 20/20 tests passing.
- **Completed Tasks**:
  - QJ-001: Supplier Quotation Data Models & Evidence Extraction (ACCEPTED)

## Verification Criteria for QJ-002
1. **Multi-Format Ingestion (`quote_judge/parser.py`)**:
   - Ingests plain text (`.txt`), Markdown (`.md`), CSV (`.csv`), JSON (`.json`), and text-based PDFs (`.pdf` via `/usr/bin/pdftotext -layout`).
   - Clean, fail-closed handling for unscanned/corrupt/OCR-only PDFs with explicit error diagnostics: "Scanned or image-only PDF detected; QuoteJudge requires selectable text and does not simulate or hallucinate OCR".
2. **Deterministic Evidence-Backed Fact Extractor (`quote_judge/extractor.py`)**:
   - Header & metadata extraction: supplier name, quote ID, quote date, validity/expiry date, currency.
   - Line items table parsing: tabular text columns, CSV records, bulleted entries.
   - Commercial totals & deductions: subtotal, discount, freight/shipping, VAT/sales tax, grand total.
   - Commercial conditions: payment terms, delivery lead time, Incoterms 2020, warranty period.
   - 100% source grounding: Every single extracted field is linked to a verified `EvidenceSpan` with exact character offsets.
3. **Automated Consistency Validation**:
   - Every ingested quotation automatically validates arithmetic consistency (`quote.validate(source_text)`).
   - Zero-hallucination guarantee: All offsets verified against raw ingested document text.
4. **Pure Standard Library & Local Tooling**:
   - Pure Python standard library with optional local POSIX binary (`/usr/bin/pdftotext`).
   - Zero external PyPI dependencies (`dependencies = []`).
5. **Comprehensive Test Suite & Demonstrations**:
   - Automated tests covering plain text, CSV, markdown tables, multilingual Arabic/English quotes, PDF text parsing, and adversarial inputs (malformed tables, zero text).

## Verification Criteria for QJ-001
1. **Typed Schemas (`quote_judge/models.py`)**:
   - `Quotation`, `LineItem`, `Terms`, `EvidenceSpan`, `Incoterm`, `Currency`, and validation results.
   - Comprehensive serialization (`to_dict`, `from_dict`) and JSON round-tripping.
2. **Exact Source Grounding (`quote_judge/evidence.py` & `EvidenceSpan`)**:
   - Explicit document identifier, page number (optional 1-indexed), line number (optional 1-indexed), character start and end offsets, and verbatim text snippet.
   - Grounding verification: methods to verify that `start_char` to `end_char` within source document exactly matches `exact_text`.
   - Utility functions to locate exact string offsets and construct verifiable `EvidenceSpan` instances.
3. **Mathematical & Business Consistency Validation**:
   - Line-item level: `unit_price * quantity` vs `total_price` (with discount tolerance).
   - Quotation level: `sum(line_items)` vs `subtotal`, and `subtotal + tax_amount + shipping_amount` vs `total_amount`.
   - Currency consistency across line items and totals.
4. **Missing Terms Auditor**:
   - Flags missing or ambiguous commercial terms: payment terms, delivery lead time, validity / expiry date, Incoterms, warranty terms, tax inclusion, shipping inclusion, MOQ.
5. **Zero External Dependencies**:
   - Pure Python standard library (dataclasses, typing, enum, math, json, re, datetime).
6. **Automated Behavioral Test Suite**:
   - 100% test pass rate covering schema validation, evidence verification, mathematical consistency, missing term detection, and adversarial edge cases.
