# QuoteJudge

> Evidence-backed supplier quotation comparison and missing terms auditor.

QuoteJudge ingests supplier quotations (structured text or PDF extracts), grounds all commercial facts (quantities, prices, Incoterms, payment conditions, delivery schedules) with exact character-level source offsets, mathematically validates quotation arithmetic, detects omitted commercial terms, and generates bilingual (Arabic/English) clarification questions.

---

## Key Features

- **Exact Source Grounding (`EvidenceSpan`)**: Links every extracted field to exact character offsets (`[start_char:end_char]`), 1-indexed line numbers, and context snippets. Verifiable directly against raw source text.
- **Mathematical & Integrity Validation**: Automatically checks line-item arithmetic (`quantity * unit_price - discount == total_price`), subtotal consistency, tax and shipping calculations, and currency uniformity across items.
- **Bilingual Missing Terms Auditor**: Detects absent or ambiguous commercial conditions:
  - Payment Terms (e.g., advance percentage, LC, net days)
  - Delivery Lead Time & Schedule
  - Validity / Expiration Date
  - Incoterms 2020 (EXW, FOB, CIF, DAP, DDP, etc.)
  - Warranty & After-Sales Guarantees
  - Tax / VAT Inclusion
  - Shipping & Freight Inclusion
  - Minimum Order Quantity (MOQ)
  Generates targeted clarification inquiries in both English and Arabic.
- **Zero External Dependencies**: 100% pure Python standard library runtime (Python 3.10+).

---

## Quickstart

### 1. Run Behavioral Test Suite
```bash
python3 -m unittest discover tests
```

### 2. Run the QJ-001 Demonstration
```bash
python3 examples/run_demo.py
```

---

## Architecture & Governance
Refer to [AGENTS.md](AGENTS.md) and [LEDGER.md](LEDGER.md) for architectural guardrails, milestone roadmaps, and execution receipts.
