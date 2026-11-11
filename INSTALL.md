# Installation & Operator Guide — QuoteJudge

> **QuoteJudge**: Evidence-Backed Supplier Quotation Comparison & Missing Terms Auditor

---

## 1. System Requirements

- **Operating System**: Linux (recommended: Ubuntu/Debian, Pop!_OS, RHEL), macOS, or Windows (WSL recommended).
- **Python Runtime**: Python 3.10, 3.11, or 3.12.
- **Third-Party PyPI Dependencies**: **None (Zero external Python dependencies)**. QuoteJudge relies entirely on the Python standard library.
- **Optional System Utility (PDF text extraction)**:
  - `pdftotext` (part of `poppler-utils` on Debian/Ubuntu/Pop!_OS: `sudo apt-get install -y poppler-utils`).
  - Required only for reading selectable text from PDF quotations. If not present or if a PDF is an image scan, QuoteJudge fails closed safely rather than simulating extraction.

---

## 2. Installation

### Option A: Editable Developer Install (Recommended)
```bash
cd "quote-judge/repo"
pip install -e .
```
This registers the CLI executable `quote-judge` in your Python environment's binary path.

### Option B: Direct Python Module Invocation (No pip install required)
QuoteJudge can be run immediately without installation:
```bash
cd "quote-judge/repo"
python3 -m quote_judge.cli --help
```

---

## 3. CLI Command Reference

QuoteJudge provides four primary subcommands:

### 3.1 `validate` — Single Quotation Arithmetic, Evidence & Missing Terms Audit
Ingests a single quotation document (`.txt`, `.md`, `.csv`, `.json`, or selectable `.pdf`), validates line-item math and subtotal arithmetic, verifies source character offsets, and audits missing terms.

```bash
# Human-readable report
quote-judge validate -f path/to/quotation.txt

# JSON output (for automated CI/CD or procurement pipelines)
quote-judge validate -f path/to/quotation.md --json
```

**Exit Codes**:
- `0`: Validation successful and arithmetic is 100% consistent.
- `1`: Validation failed due to arithmetic errors, missing file, or malformed data.
- `2`: Fail-closed refusal (`OCRRequiredError`) triggered by an image-only/scanned PDF without selectable text.

---

### 3.2 `compare` — Multi-Supplier Side-by-Side Comparison & Ranking
Ingests multiple competing quotations, aligns products using Jaccard token similarity, normalizes prices against user-supplied exchange rates, compares commercial conditions side-by-side, scores each quotation out of 100, and exports reports.

```bash
# Compare competing quotes with explicit exchange rates (e.g. SAR base)
quote-judge compare \
  -f quote_supplier1.txt quote_supplier2.csv quote_supplier3.md \
  --rates "USD=3.75,EUR=4.05,AED=1.02" \
  --base-currency SAR \
  -o comparison_report.md \
  --csv unit_prices.csv \
  --json comparison_data.json
```

**Key Parameters**:
- `-f, --files`: Two or more quotation files.
- `--rates`: Exchange rate mappings (`CURR=RATE` or JSON `{"USD": 3.75}`). If omitted, QuoteJudge preserves native currencies and will not invent rates.
- `--base-currency`: Currency to normalize scoring towards (default: `SAR`).
- `-o, --output`: Path to write the full Markdown comparison report.
- `--csv`: Path to export line-item unit price comparison CSV (equipped with spreadsheet formula injection sanitization).
- `--json`: Path to export machine-readable JSON data.

---

### 3.3 `clarify` — Bilingual Clarification Letter Generation
Generates formal bilingual (English & Arabic) commercial clarification letters for any suppliers whose quotations have omitted, ambiguous, or high-risk terms.

```bash
quote-judge clarify \
  -f quote_supplier1.txt quote_supplier2.md \
  -o ./clarification_letters \
  --buyer-company "Apex Construction LLC" \
  --contact-person "Procurement Review Committee" \
  --format md
```

Outputs formatted Markdown or JSON inquiry letters ready to transmit directly to supplier sales contacts.

---

### 3.4 `demo` — Self-Contained End-to-End Walkthrough
Runs an automated demonstration showing 3 competing quotations (Saudi SAR, UAE AED, Chinese USD), currency conversion, missing terms identification, multi-criteria scoring, and Arabic/English clarification letter generation.

```bash
quote-judge demo
```

---

## 4. Operational Boundaries & Ethical Guarantees

1. **Anti-Hallucination Currency Guarantee**:
   QuoteJudge **never** invents or fetches ungrounded live currency conversion rates. Cross-currency normalization requires explicit caller-supplied exchange rates. If unprovided, quotations remain in native currencies with clear audit warnings.

2. **Fail-Closed PDF Scanned Guardrail**:
   QuoteJudge extracts text from selectable PDFs using system utilities. When an ingested PDF contains fewer than 15 selectable characters (indicating an image or scanned document), QuoteJudge raises `OCRRequiredError` (exit code `2`) and refuses to proceed rather than hallucinating content.

3. **Spreadsheet Formula Injection Defense**:
   All CSV exports are sanitized according to OWASP guidelines: cells starting with dangerous trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) are automatically escaped with a leading single quote (`'`), while numeric negatives and Arabic right-to-left text are safely preserved.

---

## 5. Verification & Testing

Run the full automated test suite (all 67 unit and regression tests) anytime:
```bash
python3 -m unittest discover tests
```
