"""Command Line Interface for QuoteJudge.

Provides:
- validate: Ingests a quotation, validates arithmetic and source evidence, and audits missing terms.
- compare: Multi-supplier quotation comparison, line-item alignment, scoring, and multi-format export.
- clarify: Generates formal bilingual clarification letters to suppliers with missing/ambiguous terms.
- demo: Self-contained interactive demonstration comparing multi-supplier quotes.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .models import Currency, Incoterm, LineItem, Terms, Quotation
from .parser import DocumentLoader, OCRRequiredError, UnsupportedFormatError
from .extractor import QuotationExtractor
from .comparator import QuotationComparator
from .clarification import BilingualClarificationGenerator
from .export import QuotationExporter


def parse_exchange_rates_arg(rates_str: Optional[str]) -> Dict[str, float]:
    """Parses exchange rates from CLI format: 'USD=3.75,EUR=4.05' or JSON '{\"USD\": 3.75}'."""
    if not rates_str or not rates_str.strip():
        return {}

    s = rates_str.strip()
    if s.startswith("{"):
        try:
            parsed = json.loads(s)
            return {str(k).upper(): float(v) for k, v in parsed.items()}
        except Exception as e:
            raise ValueError(f"Invalid JSON exchange rates format: {e}") from e

    rates: Dict[str, float] = {}
    parts = s.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            curr, rate_val = part.split("=", 1)
        elif ":" in part:
            curr, rate_val = part.split(":", 1)
        else:
            raise ValueError(f"Malformed exchange rate entry '{part}'. Expected 'CURR=RATE' (e.g. 'USD=3.75').")

        curr = curr.strip().upper()
        try:
            rates[curr] = float(rate_val.strip())
        except ValueError as e:
            raise ValueError(f"Non-numeric rate value for {curr}: '{rate_val}'") from e

    return rates


def cmd_validate(args: argparse.Namespace) -> int:
    """Validates an individual quotation document."""
    file_path = Path(args.file)
    try:
        doc = DocumentLoader.load_file(file_path)
        extractor = QuotationExtractor()
        quote = extractor.extract(doc)
        val = quote.validate(source_text=doc.raw_text)

        if getattr(args, "json", False):
            out = {
                "document_id": doc.document_id,
                "quote_id": quote.quote_id,
                "supplier_name": quote.supplier_name,
                "currency": quote.currency.value,
                "total_amount": quote.total_amount,
                "validation": val.to_dict(),
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return 0 if val.is_valid else 1

        print("=" * 65)
        print(f"Quotation Validation Report: {file_path.name}")
        print("=" * 65)
        print(f"  Supplier:      {quote.supplier_name}")
        print(f"  Quote ID:      {quote.quote_id}")
        if quote.quote_date:
            print(f"  Date:          {quote.quote_date}")
        if quote.valid_until:
            print(f"  Valid Until:   {quote.valid_until}")
        print(f"  Currency:      {quote.currency.value}")
        print(f"  Total Amount:  {quote.total_amount:,.2f} {quote.currency.value}")
        print(f"  Line Items:    {len(quote.line_items)}")

        print("\n[Integrity Checks]")
        print(f"  Arithmetic:    {'PASS (100% Consistent)' if len(val.arithmetic_errors) == 0 else 'FAIL'}")
        for err in val.arithmetic_errors:
            print(f"    - ❌ {err}")

        print(f"  Evidence:      {'PASS (100% Grounded)' if len(val.evidence_errors) == 0 else 'FAIL'}")
        for err in val.evidence_errors:
            print(f"    - ❌ {err}")

        print(f"  Currencies:    {'PASS (Uniform)' if len(val.currency_mismatches) == 0 else 'MISMATCH'}")
        for err in val.currency_mismatches:
            print(f"    - ⚠️ {err}")

        print("\n[Missing Commercial Terms Audit]")
        if val.missing_term_alerts:
            print(f"  Detected {len(val.missing_term_alerts)} omitted or ambiguous condition(s):")
            for alert in val.missing_term_alerts:
                print(f"    - [{alert.severity}] {alert.category.value}: {alert.description_en}")
                print(f"      Clarification (EN): \"{alert.suggested_clarification_en}\"")
                print(f"      السؤال للمورد (عربي): \"{alert.suggested_clarification_ar}\"")
        else:
            print("  All essential commercial conditions are fully specified.")

        print("=" * 65)
        return 0 if val.is_valid else 1

    except OCRRequiredError as e:
        print(f"Quotation validation refused (Fail-Closed OCR Guardrail):\n{e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error validating quotation {file_path}: {e}", file=sys.stderr)
        return 1


def cmd_compare(args: argparse.Namespace) -> int:
    """Compares multiple supplier quotations side-by-side."""
    if len(args.files) < 1:
        print("Error: At least one quotation file must be specified for comparison.", file=sys.stderr)
        return 1

    try:
        rates = parse_exchange_rates_arg(getattr(args, "rates", None))
    except ValueError as e:
        print(f"Error parsing --rates: {e}", file=sys.stderr)
        return 1

    quotes: List[Quotation] = []
    extractor = QuotationExtractor()

    for f_path_str in args.files:
        f_p = Path(f_path_str)
        try:
            doc = DocumentLoader.load_file(f_p)
            q = extractor.extract(doc)
            quotes.append(q)
        except Exception as e:
            print(f"Error loading quotation '{f_p}': {e}", file=sys.stderr)
            return 1

    base_curr = getattr(args, "base_currency", "SAR")
    comparator = QuotationComparator(
        exchange_rates=rates,
        base_currency=base_curr,
    )

    report = comparator.compare(quotes)

    # Print summary table to stdout
    print(report.to_markdown_table())

    # Exports
    if getattr(args, "output", None):
        out_md = QuotationExporter.export_comparison_to_markdown(report, args.output)
        print(f"\nSaved Markdown report to: {out_md}", file=sys.stderr)

    if getattr(args, "csv", None):
        out_csv = QuotationExporter.export_comparison_to_csv(report, args.csv)
        print(f"Saved CSV summary to: {out_csv}", file=sys.stderr)

    if getattr(args, "json", None):
        out_json = QuotationExporter.export_comparison_to_json(report, args.json)
        print(f"Saved JSON data to: {out_json}", file=sys.stderr)

    return 0


def cmd_clarify(args: argparse.Namespace) -> int:
    """Generates formal bilingual clarification letters to suppliers with missing terms."""
    if len(args.files) < 1:
        print("Error: At least one quotation file must be provided.", file=sys.stderr)
        return 1

    quotes: List[Quotation] = []
    extractor = QuotationExtractor()

    for f_path_str in args.files:
        f_p = Path(f_path_str)
        try:
            doc = DocumentLoader.load_file(f_p)
            q = extractor.extract(doc)
            quotes.append(q)
        except Exception as e:
            print(f"Error loading quotation '{f_p}': {e}", file=sys.stderr)
            return 1

    comparator = QuotationComparator()
    report = comparator.compare(quotes)

    generator = BilingualClarificationGenerator(
        buyer_company=getattr(args, "buyer_company", "Procurement Department"),
        contact_person=getattr(args, "contact_person", "Procurement Committee"),
    )

    letters = generator.generate_letters_for_report(report)
    if not letters:
        print("No missing terms detected across submitted quotations. Zero clarification letters required.")
        return 0

    out_dir = Path(args.output_dir)
    fmt = getattr(args, "format", "md").lower()
    written = QuotationExporter.export_clarification_letters(letters, out_dir, format=fmt)

    print(f"Successfully generated {len(written)} clarification letter(s) in '{out_dir}':")
    for p in written:
        print(f"  - {p.name}")

    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Runs a self-contained demonstration of QuoteJudge comparison and clarification."""
    from .demo import run_demo
    return run_demo()


def build_parser() -> argparse.ArgumentParser:
    """Builds the QuoteJudge CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="quote-judge",
        description="Evidence-backed supplier quotation comparison and missing terms auditor.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="QuoteJudge subcommands")

    # 1. validate
    p_val = subparsers.add_parser("validate", help="Validate quotation arithmetic, evidence, and missing terms")
    p_val.add_argument("-f", "--file", required=True, help="Path to quotation file (.txt, .md, .csv, .json, .pdf)")
    p_val.add_argument("--json", action="store_true", help="Output results in JSON format")
    p_val.set_defaults(func=cmd_validate)

    # 2. compare
    p_cmp = subparsers.add_parser("compare", help="Compare multiple supplier quotations side-by-side")
    p_cmp.add_argument("-f", "--files", nargs="+", required=True, help="List of quotation files to compare")
    p_cmp.add_argument("-o", "--output", help="Optional path to output Markdown comparison report")
    p_cmp.add_argument("--csv", help="Optional path to export comparison CSV (with formula injection defense)")
    p_cmp.add_argument("--json", help="Optional path to export full JSON report")
    p_cmp.add_argument("--rates", help="Exchange rates mapping, e.g. 'USD=3.75,EUR=4.05' or JSON")
    p_cmp.add_argument("--base-currency", default="SAR", help="Base currency for comparison (default: SAR)")
    p_cmp.set_defaults(func=cmd_compare)

    # 3. clarify
    p_clr = subparsers.add_parser("clarify", help="Generate formal bilingual clarification letters")
    p_clr.add_argument("-f", "--files", nargs="+", required=True, help="Quotation files to evaluate")
    p_clr.add_argument("-o", "--output-dir", required=True, help="Directory to save clarification letters")
    p_clr.add_argument("--format", choices=["md", "json"], default="md", help="Letter export format (default: md)")
    p_clr.add_argument("--buyer-company", default="Procurement Department", help="Buyer company name for letterhead")
    p_clr.add_argument("--contact-person", default="Procurement Review Committee", help="Signatory contact person")
    p_clr.set_defaults(func=cmd_clarify)

    # 4. demo
    p_dmo = subparsers.add_parser("demo", help="Run comprehensive multi-supplier comparison demonstration")
    p_dmo.set_defaults(func=cmd_demo)

    return parser


def main() -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
