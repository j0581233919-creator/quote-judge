"""Document ingestion and multi-format loader for QuoteJudge.

Supports:
- Plain text (.txt, .text)
- Markdown documents (.md, .markdown)
- CSV files (.csv)
- JSON documents (.json)
- Text-based PDF documents (.pdf via standard layout-preserving pdftotext)
- Fail-closed refusal for scanned or image-only PDFs without text streams
"""

from __future__ import annotations
import csv
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Dict, Any, List


class OCRRequiredError(ValueError):
    """Raised when a PDF contains no extractable text stream (scanned/image-only)."""
    pass


class UnsupportedFormatError(ValueError):
    """Raised when a file extension is not recognized by QuoteJudge."""
    pass


@dataclass
class LoadedDocument:
    """Represents an ingested quotation document with raw text and provenance."""
    document_id: str
    file_path: Optional[str]
    file_format: str  # "txt", "md", "csv", "json", "pdf"
    raw_text: str
    line_count: int
    char_count: int
    metadata: Dict[str, Any]

    def __post_init__(self):
        self.char_count = len(self.raw_text)
        self.line_count = self.raw_text.count("\n") + 1 if self.raw_text else 0


class DocumentLoader:
    """Ingests multi-format documents while preserving bit-exact text streams."""

    SUPPORTED_EXTENSIONS = {
        ".txt": "txt",
        ".text": "txt",
        ".md": "md",
        ".markdown": "md",
        ".csv": "csv",
        ".json": "json",
        ".pdf": "pdf",
    }

    @classmethod
    def load_file(cls, file_path: Union[str, Path], document_id: Optional[str] = None) -> LoadedDocument:
        """Loads and extracts text from a file path."""
        p = Path(file_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Quotation file not found: {p}")
        if not p.is_file():
            raise ValueError(f"Path is not a regular file: {p}")

        ext = p.suffix.lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(
                f"Unsupported file format '{ext}' for file {p.name}. "
                f"Supported extensions: {', '.join(cls.SUPPORTED_EXTENSIONS.keys())}"
            )

        fmt = cls.SUPPORTED_EXTENSIONS[ext]
        doc_id = document_id or p.name

        if fmt == "pdf":
            raw_text, meta = cls._extract_pdf_text(p)
        elif fmt == "csv":
            raw_text, meta = cls._extract_csv_text(p)
        elif fmt == "json":
            raw_text, meta = cls._extract_json_text(p)
        else:
            raw_text, meta = cls._extract_plain_text(p)

        return LoadedDocument(
            document_id=doc_id,
            file_path=str(p),
            file_format=fmt,
            raw_text=raw_text,
            line_count=raw_text.count("\n") + 1 if raw_text else 0,
            char_count=len(raw_text),
            metadata=meta,
        )

    @classmethod
    def load_text(
        cls,
        text: str,
        document_id: str = "inline_quote",
        file_format: str = "txt",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LoadedDocument:
        """Loads an in-memory text string as a LoadedDocument."""
        raw_text = str(text)
        return LoadedDocument(
            document_id=document_id,
            file_path=None,
            file_format=file_format,
            raw_text=raw_text,
            line_count=raw_text.count("\n") + 1 if raw_text else 0,
            char_count=len(raw_text),
            metadata=metadata or {},
        )

    @classmethod
    def _extract_plain_text(cls, path: Path) -> tuple[str, Dict[str, Any]]:
        """Reads plain text or markdown file with multi-encoding fallback."""
        encodings = ["utf-8", "utf-8-sig", "cp1256", "latin-1"]
        last_err: Optional[Exception] = None

        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                return content, {"encoding": enc}
            except UnicodeDecodeError as e:
                last_err = e
                continue

        raise ValueError(f"Failed to decode text file {path}: {last_err}")

    @classmethod
    def _extract_csv_text(cls, path: Path) -> tuple[str, Dict[str, Any]]:
        """Reads CSV file raw text while validating parseability."""
        content, meta = cls._extract_plain_text(path)
        # Verify CSV structure
        lines = content.strip().splitlines()
        if not lines:
            raise ValueError(f"CSV file is empty: {path}")

        reader = csv.reader(lines)
        row_count = sum(1 for _ in reader)
        meta["csv_rows"] = row_count
        return content, meta

    @classmethod
    def _extract_json_text(cls, path: Path) -> tuple[str, Dict[str, Any]]:
        """Reads JSON file raw text while validating JSON syntax."""
        content, meta = cls._extract_plain_text(path)
        try:
            parsed = json.loads(content)
            meta["json_keys"] = list(parsed.keys()) if isinstance(parsed, dict) else len(parsed)
            return content, meta
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON in file {path}: {e}") from e

    @classmethod
    def _extract_pdf_text(cls, path: Path) -> tuple[str, Dict[str, Any]]:
        """Extracts text streams from text-based PDF using standard system pdftotext.
        
        Strictly fails closed if the PDF contains no selectable text (scanned/raster images).
        """
        # Check pdftotext binary availability
        bin_path = "/usr/bin/pdftotext"
        if not os.path.exists(bin_path):
            import shutil
            bin_path = shutil.which("pdftotext")
            if not bin_path:
                raise RuntimeError(
                    "The 'pdftotext' system utility (poppler-utils) is required for PDF ingestion. "
                    "Alternatively, pass pre-extracted text, Markdown, or CSV."
                )

        try:
            cmd = [bin_path, "-layout", str(path), "-"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                raise ValueError(
                    f"pdftotext execution failed (exit code {result.returncode}): {result.stderr.strip()}"
                )

            extracted_text = result.stdout

            # Scanned / Image-only PDF detection
            # If the PDF produces virtually no characters or only whitespace/newlines
            cleaned_text = extracted_text.strip()
            if len(cleaned_text) < 15:
                raise OCRRequiredError(
                    f"PDF document '{path.name}' contains no extractable text stream. "
                    f"It appears to be a scanned image or raster PDF. "
                    f"QuoteJudge strictly operates on verifiable text and does not simulate or hallucinate OCR."
                )

            meta = {
                "extractor": "pdftotext",
                "layout_mode": True,
            }
            return extracted_text, meta

        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"PDF extraction timed out after 15 seconds for {path}") from e
        except OCRRequiredError:
            raise
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF {path}: {e}") from e
