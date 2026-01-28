"""Athena adapters package."""

__all__ = ["extract_text_from_pdf", "scan_pdf_directory"]

from .pdf_adapter import extract_text_from_pdf, scan_pdf_directory
