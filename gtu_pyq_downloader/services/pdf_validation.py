"""PDF validation utilities for ensuring file integrity.

Provides functions to validate that files are legitimate PDFs with at least
one page before attempting to use them in merging operations.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def is_valid_pdf(path: Path) -> bool:
    """Check if a file is a valid PDF with at least one page.
    
    Args:
        path: Path to the file to validate
        
    Returns:
        True if the file exists and is a valid PDF with page(s), False otherwise.
        Returns False on any error (file not found, parse error, etc.)
    """
    try:
        reader = PdfReader(str(path))
        return len(reader.pages) > 0
    except Exception:
        return False
