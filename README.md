# QuoteJudge

> Evidence-backed supplier quotation comparison and missing terms auditor.

QuoteJudge ingests supplier quotations (structured text, Markdown, CSV, JSON, or selectable PDF), grounds all commercial facts (quantities, prices, Incoterms, payment conditions, delivery schedules) with exact character-level source offsets, mathematically validates quotation arithmetic, audits omitted or ambiguous commercial terms, ranks competing suppliers with multi-criteria scoring, and generates formal bilingual (Arabic/English) clarification letters.

---

## Key Features

- **Exact Source Evidence Grounding (`EvidenceSpan`)**: Links every extracted field to exact character offsets (`[start_char:end_char]`), 1-indexed line numbers, and context snippets. Verifiable directly against raw source text.
- **Mathematical & Integrity Validation**: Automatically checks line-item arithmetic (`quantity * unit_price == total_price`), subtotal consistency, tax and shipping calculations, and currency uniformity across items.
- **Multi-Format Ingestion Engine**: Seamlessly processes `.txt`, `.md`, `.csv`, `.json`, and selectable `.pdf` documents with fail-closed refusal (`OCRRequiredError`) on image-only/scanned PDFs to prevent hallucinated data.
- **Side-by-Side Quotation Comparison Engine**:
  - Jaccard token similarity for flexible product description alignment across diverse supplier nomenclatures.
  - Multi-criteria weighted scoring (price, delivery speed, warranty duration, terms completeness).
  - Anti-hallucination currency handling (requires explicit exchange rates or preserves native currencies).
- **Bilingual Missing Terms Auditor & Clarification Letters**: Detects absent or ambiguous commercial conditions:
  - Payment Terms (advance percentage, LC, net days)
  - Delivery Lead Time & Schedule
  - Validity / Expiration Date
  - Incoterms 2020 (EXW, FOB, CIF, DAP, DDP, etc.)
  - Warranty & After-Sales Guarantees
  - Tax / VAT Inclusion
  - Shipping & Freight Inclusion
  - Minimum Order Quantity (MOQ)
  Generates targeted, formal clarification inquiry letters in both English and Arabic.
- **Spreadsheet Security (OWASP-Compliant)**: CSV exports automatically neutralize formula injection vectors (`=`, `+`, `-`, `@`, `\t`, `\r`) while preserving valid negative numbers and Arabic strings.
- **Zero External Python Dependencies**: 100% pure Python standard library runtime (Python 3.10+).

---

## Quickstart

### 1. Run Automated Test Suite (67 Passing Tests)
```bash
python3 -m unittest discover tests
```

### 2. Run the Interactive Demonstration
```bash
python3 -m quote_judge.cli demo
```

### 3. Validate a Quotation
```bash
python3 -m quote_judge.cli validate -f path/to/quotation.txt
```

### 4. Compare Competing Quotations
```bash
python3 -m quote_judge.cli compare \
  -f supplier_a.txt supplier_b.csv supplier_c.md \
  --rates "USD=3.75,EUR=4.05,AED=1.02" \
  --base-currency SAR \
  -o comparison_report.md \
  --csv unit_prices.csv
```

### 5. Generate Clarification Letters
```bash
python3 -m quote_judge.cli clarify \
  -f supplier_a.txt supplier_b.csv \
  -o ./clarification_letters \
  --buyer-company "Apex Construction LLC"
```

---

## Installation & Operator Guide

See [INSTALL.md](INSTALL.md) for detailed installation options, CLI reference, and operational boundaries.

---

## Architecture & Governance

Refer to [AGENTS.md](AGENTS.md) and [LEDGER.md](LEDGER.md) for architectural guardrails, milestone roadmaps, and execution receipts.
