"""Export engine and spreadsheet security defenses for QuoteJudge.

Provides:
- CSV / Excel Formula Injection (DDE attack) neutralization
- Structured CSV comparison table export
- Comprehensive Markdown report export
- Machine-readable JSON export with full roundtrip fidelity
- Batch clarification letter exporter
"""

from __future__ import annotations
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .comparator import ComparisonReport
from .clarification import ClarificationLetter

_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_NUMERIC_PATTERN = re.compile(r"^[-+]?\d+(?:\.\d+)?$")


def is_potentially_dangerous_formula(val: Any) -> bool:
    """Detects whether a cell value begins with a spreadsheet formula trigger without being a pure number."""
    if val is None or not isinstance(val, str):
        return False
    if not val:
        return False
    # Check leading control characters before stripping
    if val.startswith(("\t", "\r")):
        return True
    s = val.strip()
    if not s:
        return False
    if s.startswith(_DANGEROUS_PREFIXES):
        # Allow benign strictly numeric strings (e.g., -5, +10, -120.50)
        if _NUMERIC_PATTERN.match(s):
            return False
        return True
    return False


def sanitize_csv_cell(val: Any) -> str:
    """Escapes dangerous formula cells by prepending a leading single quote."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)

    s = str(val)
    if is_potentially_dangerous_formula(s):
        return f"'{s}"
    return s


def desanitize_csv_cell(val: str) -> str:
    """Reverses CSV formula sanitization if leading quote was prepended for escaping."""
    if not val:
        return ""
    if val.startswith("'") and len(val) > 1:
        rest = val[1:]
        if is_potentially_dangerous_formula(rest):
            return rest
    return val


def sanitize_csv_row(row: Dict[str, Any]) -> Dict[str, str]:
    """Sanitizes all cell values in a dictionary row for safe CSV writing."""
    return {k: sanitize_csv_cell(v) for k, v in row.items()}


def desanitize_csv_row(row: Dict[str, str]) -> Dict[str, str]:
    """Desanitizes all cell values in a dictionary row read from a sanitized CSV."""
    return {k: desanitize_csv_cell(v) for k, v in row.items()}


class QuotationExporter:
    """Exports comparison reports and clarification letters into secure, structured formats."""

    @classmethod
    def export_comparison_to_csv(
        cls,
        report: ComparisonReport,
        output_path: Union[str, Path],
        overwrite: bool = True,
    ) -> Path:
        """Exports line-item comparison table to CSV with formula injection defense."""
        p = Path(output_path).resolve()
        if p.exists() and not overwrite:
            raise FileExistsError(f"Destination CSV file already exists: {p}")

        p.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["product_description"] + [f"{s}_unit_price" for s in report.suppliers] + ["lowest_price_supplier", "price_spread_percent", "uom"]

        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item_comp in report.item_comparisons:
                row_raw: Dict[str, Any] = {
                    "product_description": item_comp.canonical_description,
                    "lowest_price_supplier": item_comp.lowest_price_supplier,
                    "price_spread_percent": round(item_comp.price_spread_percent, 2),
                    "uom": item_comp.unit_of_measure,
                }
                for sup in report.suppliers:
                    matched = item_comp.matched_items.get(sup)
                    if matched:
                        row_raw[f"{sup}_unit_price"] = matched.unit_price
                    else:
                        row_raw[f"{sup}_unit_price"] = ""

                # Sanitize entire row against formula injection
                writer.writerow(sanitize_csv_row(row_raw))

        return p

    @classmethod
    def export_comparison_to_markdown(
        cls,
        report: ComparisonReport,
        output_path: Union[str, Path],
        overwrite: bool = True,
    ) -> Path:
        """Exports comparison report to formatted Markdown."""
        p = Path(output_path).resolve()
        if p.exists() and not overwrite:
            raise FileExistsError(f"Destination Markdown file already exists: {p}")

        p.parent.mkdir(parents=True, exist_ok=True)
        content = report.to_markdown_table()
        p.write_text(content, encoding="utf-8")
        return p

    @classmethod
    def export_comparison_to_json(
        cls,
        report: ComparisonReport,
        output_path: Union[str, Path],
        overwrite: bool = True,
        indent: int = 2,
    ) -> Path:
        """Exports comparison report to structured JSON."""
        p = Path(output_path).resolve()
        if p.exists() and not overwrite:
            raise FileExistsError(f"Destination JSON file already exists: {p}")

        p.parent.mkdir(parents=True, exist_ok=True)
        data = report.to_dict()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return p

    @classmethod
    def export_clarification_letters(
        cls,
        letters: Dict[str, ClarificationLetter],
        output_dir: Union[str, Path],
        format: str = "md",
        overwrite: bool = True,
    ) -> List[Path]:
        """Exports clarification letters to individual files in a target directory."""
        d = Path(output_dir).resolve()
        d.mkdir(parents=True, exist_ok=True)
        written_paths: List[Path] = []

        for sup_name, letter in letters.items():
            safe_name = re.sub(r"[^\w\s-]", "", sup_name).strip().replace(" ", "_")
            if format.lower() == "json":
                out_p = d / f"clarification_{safe_name}.json"
                if out_p.exists() and not overwrite:
                    continue
                with open(out_p, "w", encoding="utf-8") as f:
                    json.dump(letter.to_dict(), f, indent=2, ensure_ascii=False)
            else:
                out_p = d / f"clarification_{safe_name}.md"
                if out_p.exists() and not overwrite:
                    continue
                out_p.write_text(letter.to_markdown(language="bilingual"), encoding="utf-8")

            written_paths.append(out_p)

        return written_paths
