# AGENTS.md — QuoteJudge

## Authority & Mission
QuoteJudge is an evidence-backed supplier quotation comparison system designed to ingest text-based supplier quotations (e.g., PDF/text), extract structured prices, quantities, terms, and units with exact source grounding, identify missing or conflicting terms, compare competing quotes side-by-side, and produce bilingual clarification questions.

## Core Rules & Guardrails
1. **Source Grounding**: Every extracted fact (unit price, total price, currency, payment terms, delivery lead time, MOQ, Incoterms) must be linked to exact source evidence (page, bounding/text offset, or excerpt).
2. **No Hallucinated OCR or Exchange Rates**: Never invent OCR text or fabricate exchange rates. If a currency conversion is required, state the explicit conversion rate used or preserve quotes in original currencies with comparison notes.
3. **Missing Terms Detection**: Explicitly detect and highlight missing terms (e.g., warranty, shipping fees, tax/VAT inclusion, validity period).
4. **Side-by-Side Comparison**: Generate structured tabular comparison and clear exportable summaries (JSON, CSV, Markdown).
5. **Bilingual Clarification**: Formulate clear supplier clarification inquiries in Arabic and English for missing or ambiguous terms.
6. **Independence**: Flash must not certify its own implementation as independently reviewed. Codex or independent reviewer certifies review status.

## Lifecycle States
`READY` -> `IN_PROGRESS` -> `IMPLEMENTED` -> `TESTED` -> `REVIEW_PENDING` -> `ACCEPTED` -> `RELEASE_READY`
