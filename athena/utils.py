"""
Text chunking utilities for Athena.

Split documents into overlapping chunks while preserving structure.
"""

from typing import Optional


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    preserve_paragraphs: bool = True,
) -> list[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text to chunk
        chunk_size: Target chunk size (characters)
        chunk_overlap: Overlap between chunks
        preserve_paragraphs: Avoid splitting within paragraphs
    
    Returns:
        List of text chunks
    """
    if not text or len(text) < chunk_size:
        return [text] if text else []

    chunks = []
    start = 0

    while start < len(text):
        # Find chunk end
        end = min(start + chunk_size, len(text))

        # If not at end of text and preserve_paragraphs, find paragraph boundary
        if end < len(text) and preserve_paragraphs:
            # Look for newline within last 50 chars
            last_newline = text.rfind("\n", max(start, end - 50), end)
            if last_newline > start:
                end = last_newline

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        start = end - chunk_overlap if end < len(text) else len(text)

    return chunks


def clean_text(text: str) -> str:
    """
    Normalize text for processing.
    
    - Remove extra whitespace
    - Normalize newlines
    """
    if not text:
        return ""

    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove extra spaces
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove excessive blank lines
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text.strip()


def sanitize_filename(filename: str) -> str:
    """Remove/replace invalid filename characters."""
    invalid = r'<>:"/\|?*'
    sanitized = filename
    for char in invalid:
        sanitized = sanitized.replace(char, "_")
    return sanitized
