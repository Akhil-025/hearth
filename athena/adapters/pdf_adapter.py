"""
PDF text extraction adapter for Athena.

Extract text from PDF files with page tracking.
"""

from pathlib import Path
from typing import Optional

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


def extract_text_from_pdf(pdf_path: Path) -> tuple[str, dict]:
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Tuple of (full_text, metadata)
        metadata includes page count and structure
    
    Raises:
        ImportError: If PyPDF2 not installed
        FileNotFoundError: If PDF not found
    """
    if PdfReader is None:
        raise ImportError(
            "PyPDF2 required for PDF support. Install with: pip install PyPDF2"
        )

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        reader = PdfReader(str(pdf_path))
        pages = reader.pages
        full_text = ""
        page_breaks = {}  # Map position to page number

        for page_num, page in enumerate(pages, start=1):
            page_breaks[len(full_text)] = page_num
            text = page.extract_text()
            if text:
                full_text += f"\n--- Page {page_num} ---\n{text}\n"

        metadata = {
            "page_count": len(pages),
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "page_breaks": page_breaks,
        }

        return full_text, metadata

    except Exception as e:
        raise RuntimeError(f"Failed to extract text from {pdf_path}: {e}")


def scan_pdf_directory(data_dir: Path) -> list[Path]:
    """
    Recursively scan directory for PDF files.
    
    Args:
        data_dir: Root directory to scan
    
    Returns:
        List of PDF file paths
    """
    if not data_dir.is_dir():
        return []

    pdf_files = []
    for pdf_file in data_dir.rglob("*.pdf"):
        if pdf_file.is_file() and not pdf_file.name.startswith("."):
            pdf_files.append(pdf_file)

    return sorted(pdf_files)


def get_text_with_page_numbers(
    pdf_path: Path, text: str, page_breaks: dict
) -> list[tuple[str, int]]:
    """
    Split extracted text into lines with page numbers.
    
    Args:
        pdf_path: Original PDF path (for reference)
        text: Full extracted text
        page_breaks: Map of text position to page number
    
    Returns:
        List of (text_line, page_number) tuples
    """
    lines = text.split("\n")
    result = []
    current_page = 1
    text_position = 0

    for line in lines:
        # Update page number if we've reached a page break
        for pos, page_num in sorted(page_breaks.items()):
            if text_position >= pos:
                current_page = page_num

        if line.strip():
            result.append((line.strip(), current_page))

        text_position += len(line) + 1  # +1 for newline

    return result
