import logging
from pathlib import Path
from typing import List, Dict
from pypdf import PdfWriter, PdfReader

logger = logging.getLogger(__name__)


def merge_pdfs(paths: List[Path], out_path: Path) -> Dict:
    writer = PdfWriter()
    total_pages = 0
    for p in paths:
        try:
            reader = PdfReader(str(p))
            for page in reader.pages:
                writer.add_page(page)
            total_pages += len(reader.pages)
        except Exception as exc:
            logger.error("Skipping corrupt PDF %s: %s", p, exc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        writer.write(fh)
    logger.info("Wrote merged PDF %s (%d pages)", out_path, total_pages)
    return {"merged_path": str(out_path), "total_pages": total_pages}
