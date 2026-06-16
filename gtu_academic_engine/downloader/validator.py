import logging
from pathlib import Path
from typing import Optional
from pypdf import PdfReader
from ..constants import PDF_MAGIC_BYTES, VALID_PDF_MIN_SIZE

logger = logging.getLogger(__name__)


def is_valid_pdf(path: Path) -> bool:
    """Validate a PDF file by checking magic bytes, size, and structure.
    
    Args:
        path: Path to the PDF file
        
    Returns:
        True if valid PDF, False otherwise
    """
    if not path.exists():
        logger.debug("PDF missing: %s", path)
        return False
    
    # Quick check: file size
    file_size = path.stat().st_size
    if file_size < VALID_PDF_MIN_SIZE:
        logger.warning("PDF file too small (%d bytes): %s", file_size, path)
        return False
    
    # Quick check: magic bytes
    try:
        with path.open("rb") as f:
            header = f.read(len(PDF_MAGIC_BYTES))
            if header != PDF_MAGIC_BYTES:
                logger.warning("Invalid PDF magic bytes: %s", path)
                return False
    except Exception as exc:
        logger.error("Failed to read PDF magic bytes %s: %s", path, exc)
        return False
    
    # Full validation: parse PDF structure
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            logger.warning("PDF encrypted: %s", path)
            return False
        num = len(reader.pages)
        if num == 0:
            logger.warning("PDF has zero pages: %s", path)
            return False
        return True
    except Exception as exc:
        logger.error("Invalid PDF %s: %s", path, exc)
        return False


def validate_bytes(data: Optional[bytes]) -> bool:
    """Validate PDF bytes without writing to disk.
    
    Args:
        data: Bytes of the PDF file
        
    Returns:
        True if valid PDF, False otherwise
    """
    if not data:
        return False
    
    # Quick check: size
    if len(data) < VALID_PDF_MIN_SIZE:
        return False
    
    # Quick check: magic bytes
    if not data.startswith(PDF_MAGIC_BYTES):
        return False
    
    # Full validation: parse structure
    try:
        from io import BytesIO
        reader = PdfReader(BytesIO(data))
        return len(reader.pages) > 0
    except Exception:
        return False
