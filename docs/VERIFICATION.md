# Verification & Quality Assurance Runbook

## Automated Test Execution

QuoteJudge maintains a 100% automated test suite using Python's standard `unittest` framework:

```bash
# Execute entire test suite
python3 -m unittest discover tests -v
```

### Test Suite Structure
- `tests/test_models.py`: Evidence span tracking, currency validation, and quotation models.
- `tests/test_parser.py`: Text parser, line-item table extraction, OCR refusal (`OCRRequiredError`), and evidence grounding.
- `tests/test_auditor.py`: Arithmetic discrepancy detection, subtotal/tax recalculation, and missing commercial terms auditing.
- `tests/test_comparator.py`: Multi-supplier quotation comparison, currency conversion, score rankings, and export formatting.
- `tests/test_packaging_and_cli.py`: Subcommand testing (`validate`, `compare`, `clarify`, `demo`), exit codes (0, 1, 2), and CLI arguments.

## Verification Gate Checklist
1. All 67 unit and regression tests pass with 0 failures and 0 errors.
2. CLI subcommands (`quote-judge --help`, `quote-judge demo`, `quote-judge validate`) execute cleanly.
3. Clean installation via `pip install .` in isolated virtual environment executes successfully without network access.
