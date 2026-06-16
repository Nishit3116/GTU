from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def standardize_pdf_name(session: str, subject_code: str) -> str:
    """Standardize PDF file naming: S2026_3170719.pdf"""
    return f"{session}_{subject_code}.pdf"


def standardize_merged_name(subject_code: str, from_year: int, to_year: int) -> str:
    """Standardize merged PDF naming: 3170719_PYQ_2026_2021.pdf"""
    return f"{subject_code}_PYQ_{to_year}_{from_year}.pdf"


def standardize_report_name(subject_code: str) -> str:
    """Standardize report naming: 3170719_report.txt"""
    return f"{subject_code}_report.txt"


def standardize_metadata_name(subject_code: str) -> str:
    """Standardize metadata naming: 3170719_metadata.json"""
    return f"{subject_code}_metadata.json"


def cleanup_folder(folder: Path) -> None:
    """Remove empty subfolders and corrupt/temp files."""
    if not folder.exists():
        return

    # Remove empty directories recursively
    for item in folder.rglob("*"):
        if item.is_dir() and not any(item.iterdir()):
            try:
                item.rmdir()
                logger.info("Removed empty folder: %s", item)
            except Exception as exc:
                logger.warning("Failed to remove folder %s: %s", item, exc)

    # Remove temp/state files
    for pattern in [".*.state.json", "*.tmp"]:
        for item in folder.glob(pattern):
            try:
                item.unlink()
                logger.info("Removed temp file: %s", item)
            except Exception as exc:
                logger.warning("Failed to remove %s: %s", item, exc)
