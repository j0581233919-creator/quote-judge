# Security Policy

## Scope & Operational Context

`quote-judge` is an evidence-backed quotation comparison and missing terms auditor designed to ingest structured or raw text supplier quotations, verify line-item arithmetic and tax math, detect missing commercial terms (incoterms, payment terms, delivery schedules, warranties), and produce multi-currency normalized comparisons.

It is intended for local execution or integration into enterprise procurement pipelines. It is **not** an internet-facing authorization server or legal contract notary.

## Security Guarantees & Defenses

1. **Evidence-Grounded Extraction**:
   - Every extracted quotation datum (price, currency, tax, term) binds directly to exact character spans in the raw quotation document.
   - Values without verifiable textual evidence are rejected or flagged as missing.

2. **Scanned PDF & Image Refusal (Fail-Closed)**:
   - When fed scanned documents without readable text or corrupt PDF streams, `quote-judge` safely raises `OCRRequiredError` (CLI exit code 2) rather than fabricating or guessing figures.

3. **CSV Formula Injection Mitigation**:
   - Comparison and audit tables exported to CSV escape dangerous spreadsheet trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with leading single quotes to prevent code/formula execution in Excel or Calc.

4. **Tamper-Evident Hashing**:
   - Comparison reports and clarification letters compute SHA-256 integrity digests over normalized representations.

5. **Pure Standard Library Runtime**:
   - Zero third-party PyPI dependencies, eliminating external package vulnerabilities or malicious dependencies.

## Reporting a Vulnerability

If you discover a security vulnerability in `quote-judge`, please report it responsibly:
- Email: `security@localhost` (or contact maintainers via GitHub Security Advisories).
- Please include reproduction steps and sample input document.
