"""Syllabus downloader for GTU Academic Engine V2.

Downloads syllabus PDFs for a selected subject, storing them alongside
the PYQ downloads in the structured folder hierarchy.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"


def _validate_pdf_bytes(data: bytes) -> bool:
    """Return True if bytes look like a valid PDF."""
    return bool(data) and data[:4] == _PDF_MAGIC


def _structured_output_dir(
    subject: dict,
    base_dir: Path,
) -> Path:
    """Build the structured download path from a subject dict.

    Pattern:
        {base_dir}/{course}/{branch}/{year}/{semester}/{elective}/{subject_name}/
    """
    course = subject.get("course", "Unknown")
    branch = subject.get("branch_name") or subject.get("branch", "Unknown")
    year = subject.get("academic_year", "Unknown")
    semester = subject.get("semester_label") or f"Semester_{subject.get('semester', '?')}"
    elective = subject.get("elective_type", "Unknown")
    subject_name = (subject.get("subject_name") or subject.get("subject_code", "Unknown"))
    # Sanitise path components
    def safe(s: str) -> str:
        return "".join(c if c.isalnum() or c in " _-" else "_" for c in str(s)).strip()

    return (
        base_dir
        / safe(course)
        / safe(branch)
        / safe(year)
        / safe(semester)
        / safe(elective)
        / safe(subject_name)
    )


class SyllabusDownloader:
    """Downloads syllabus PDFs for selected subjects.

    Uses the ASPXProvider for live discovery, or falls back to direct URL
    patterns.  Saves to the structured output hierarchy.

    Usage::

        dl = SyllabusDownloader(base_dir=Path("downloads"))
        path = dl.download(subject_dict)
        if path:
            print(f"Saved: {path}")
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        provider=None,
    ) -> None:
        """
        Args:
            base_dir: Root downloads directory.  Defaults to config.downloads_dir.
            provider: Optional ASPXProvider instance.  If not given, a headless
                      instance is created on demand.
        """
        if base_dir is None:
            try:
                from gtu_academic_engine.config import config
                base_dir = config.downloads_dir
            except Exception:
                base_dir = Path("downloads")
        self._base_dir = base_dir
        self._provider = provider

    def download(self, subject: dict) -> Optional[Path]:
        """Download syllabus for a subject and save it.

        Args:
            subject: Subject dict from SubjectSelector / academic data.
                     Needs at minimum: subject_code.

        Returns:
            Path to saved syllabus.pdf on success, None on failure.
        """
        subject_code = subject.get("subject_code")
        if not subject_code:
            logger.error("Subject dict missing subject_code")
            return None

        out_dir = _structured_output_dir(subject, self._base_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "syllabus.pdf"

        # Check existing valid file
        if dest.exists() and dest.stat().st_size > 1000:
            with dest.open("rb") as fh:
                if _validate_pdf_bytes(fh.read(8)):
                    logger.info("Syllabus already downloaded: %s", dest)
                    print(f"  ✓ Using existing syllabus: {dest}")
                    return dest

        print(f"  Downloading syllabus for {subject.get('subject_name', subject_code)}…")

        pdf_bytes = None
        pdf_url = subject.get("syllabus_pdf_url")
        if pdf_url:
            logger.info("Found syllabus_pdf_url in subject: %s", pdf_url)
            pdf_bytes = self._download_direct_url(pdf_url)

        # Try via provider
        if not pdf_bytes:
            pdf_bytes = self._download_via_provider(subject)

        # Fallback: direct URL patterns
        if not pdf_bytes:
            pdf_bytes = self._download_direct(subject_code)

        if not pdf_bytes:
            print(f"  ✗ Syllabus not found for {subject_code}")
            logger.warning("Syllabus download failed for %s", subject_code)
            return None

        if not _validate_pdf_bytes(pdf_bytes):
            print(f"  ✗ Downloaded data is not a valid PDF for {subject_code}")
            logger.warning("Invalid PDF received for syllabus %s", subject_code)
            return None

        dest.write_bytes(pdf_bytes)
        print(f"  ✓ Syllabus saved: {dest}")
        logger.info("Saved syllabus %s → %s (%d bytes)", subject_code, dest, len(pdf_bytes))
        return dest

    @staticmethod
    def _download_direct_url(url: str) -> Optional[bytes]:
        """Download PDF from a specific URL."""
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://gtu.ac.in/syllabus/syllabus.aspx",
        }
        try:
            r = requests.get(url, timeout=15, headers=headers)
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                logger.info("Downloaded syllabus from direct URL %s", url)
                return r.content
        except Exception as exc:
            logger.debug("Direct URL download failed: %s", exc)
        return None

    def _download_via_provider(self, subject: dict) -> Optional[bytes]:
        """Attempt to download via ASPXProvider.download_syllabus()."""
        try:
            if self._provider is None:
                from gtu_academic_engine.provider.aspx_provider import ASPXProvider
                with ASPXProvider(headless=True) as prov:
                    return prov.download_syllabus(subject["subject_code"])
            else:
                return self._provider.download_syllabus(subject["subject_code"])
        except Exception as exc:
            logger.debug("Provider syllabus download failed: %s", exc)
            return None

    @staticmethod
    def _download_direct(subject_code: str) -> Optional[bytes]:
        """Try well-known direct URL patterns for GTU syllabus PDFs."""
        import requests

        patterns = [
            f"https://gtu.ac.in/syllabus/{subject_code}.pdf",
            f"https://gtu.ac.in/uploads/syllabus/{subject_code}.pdf",
            f"https://gtu.ac.in/syllabus/uploads/{subject_code}.pdf",
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://gtu.ac.in/syllabus/syllabus.aspx",
        }
        for url in patterns:
            try:
                r = requests.get(url, timeout=15, headers=headers)
                if r.status_code == 200 and r.content[:4] == b"%PDF":
                    logger.info("Downloaded syllabus from %s", url)
                    return r.content
            except Exception as exc:
                logger.debug("URL %s → %s", url, exc)
        return None


def get_structured_output_dir(subject: dict, base_dir: Path) -> Path:
    """Public helper to get the structured output directory for a subject."""
    return _structured_output_dir(subject, base_dir)
