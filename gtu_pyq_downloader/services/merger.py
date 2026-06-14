from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .pdf_validation import is_valid_pdf


class PDFMergerService:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def merge(self, pdf_paths: list[Path], output_path: Path) -> int:
        writer = PdfWriter()
        merged_count = 0

        for pdf_path in pdf_paths:
            if not pdf_path.exists():
                self._logger.warning("Skipping missing file during merge: %s", pdf_path)
                continue

            if not is_valid_pdf(pdf_path):
                self._logger.warning("Skipping invalid PDF during merge: %s", pdf_path)
                continue

            try:
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)
                merged_count += 1
            except Exception:
                self._logger.exception("Skipping unreadable PDF during merge: %s", pdf_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as handle:
            writer.write(handle)

        return merged_count
