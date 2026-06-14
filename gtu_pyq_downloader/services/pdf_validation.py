from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def is_valid_pdf(path: Path) -> bool:
    try:
        reader = PdfReader(str(path))
        return len(reader.pages) > 0
    except Exception:
        return False
