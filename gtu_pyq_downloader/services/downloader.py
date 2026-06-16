"""PDF downloader service for GTU papers.

Implements robust PDF download with:
- Repository-based search (primary method)
- Direct URL fallback (secondary method)
- Retry logic with exponential backoff
- SHA256 duplicate detection
- PDF validation before saving
- Smart reuse of existing valid PDFs
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from ..config import GTUPYQConfig
from ..models import PaperResult, PaperStatus
from .repository import GTUPaperRepositoryClient
from .pdf_validation import is_valid_pdf


class GTUPYQDownloader:
    """Downloads GTU papers for a given subject code and session.
    
    Strategy:
    1. Try repository URLs (from search_pdf_urls)
    2. Fall back to direct base URL with retries
    3. Reuse valid existing files
    4. Skip missing files without failing the entire run
    """
    
    def __init__(self, config: GTUPYQConfig, logger: logging.Logger) -> None:
        """Initialize downloader with configuration, logger, and HTTP session.
        
        Args:
            config: GTUPYQConfig instance with URLs and request settings
            logger: Logger instance for operation tracking
        """
        self._config = config
        self._logger = logger
        self._session = requests.Session()
        self._session.headers.update(config.request_headers)
        self._repository = GTUPaperRepositoryClient(config, logger)
        self._repository.bootstrap()

    def close(self) -> None:
        """Close HTTP sessions and cleanup resources."""
        self._session.close()
        self._repository.close()

    def ensure_subject_folder(self, subject_code: str) -> Path:
        """Create subject directory if it doesn't exist.
        
        Args:
            subject_code: GTU subject code
            
        Returns:
            Path to the subject directory
        """
        folder = self._config.subject_directory(subject_code)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def fetch_paper(self, subject_code: str, session: str) -> PaperResult:
        """Download or reuse a PDF for a given subject and session.
        
        Tries in this order:
        1. Return existing valid PDF
        2. Search repository for URLs and download
        3. Fall back to direct base URL with retries
        4. Return appropriate status (NOT_FOUND, BLOCKED, FAILED, etc.)
        
        Args:
            subject_code: GTU subject code
            session: Session code (e.g., "W2026", "S2026")
            
        Returns:
            PaperResult with status, file path (if successful), and message
        """
        folder = self.ensure_subject_folder(subject_code)
        file_path = folder / f"{session}_{subject_code}.pdf"

        if file_path.exists():
            if is_valid_pdf(file_path):
                self._logger.info("Reusing valid PDF: %s", file_path)
                return PaperResult(
                    session=session,
                    status=PaperStatus.EXISTS,
                    file_path=file_path,
                    message="Existing valid PDF reused",
                )

            self._logger.warning("Removing corrupted PDF: %s", file_path)
            file_path.unlink(missing_ok=True)

        last_error = ""

        repository_urls = self._repository.search_pdf_urls(subject_code, session)
        if repository_urls:
            for repository_url in repository_urls:
                try:
                    data = self._repository.download_bytes(repository_url)
                    # compute sha256 and detect duplicates
                    import hashlib

                    sha = hashlib.sha256(data).hexdigest()
                    # check existing files in folder for same hash
                    for existing in folder.glob(f"*_{subject_code}.pdf"):
                        try:
                            if existing.exists():
                                if hashlib.sha256(existing.read_bytes()).hexdigest() == sha:
                                    self._logger.info("Duplicate detected. Skipping save, using %s", existing)
                                    return PaperResult(
                                        session=session,
                                        status=PaperStatus.EXISTS,
                                        file_path=existing,
                                        message=f"Duplicate of {existing.name}",
                                    )
                        except Exception:
                            continue

                    file_path.write_bytes(data)

                    if is_valid_pdf(file_path):
                        self._logger.info("Downloaded PDF from repository: %s", file_path)
                        return PaperResult(
                            session=session,
                            status=PaperStatus.DOWNLOADED,
                            file_path=file_path,
                            message="Downloaded successfully",
                        )

                    last_error = "Repository download failed PDF validation"
                    self._logger.warning("Invalid PDF received from repository: %s", repository_url)
                    file_path.unlink(missing_ok=True)
                except requests.RequestException as exc:
                    last_error = str(exc)
                    self._logger.warning("Repository download failed for %s: %s", repository_url, last_error)
                except OSError as exc:
                    last_error = str(exc)
                    self._logger.exception("File write failed for %s", file_path)
                    return PaperResult(
                        session=session,
                        status=PaperStatus.FAILED,
                        message=last_error,
                    )

        url = self._config.base_url.format(session=session, subject_code=subject_code)
        for attempt in range(1, self._config.max_retries + 1):
            try:
                response = self._session.get(
                    url,
                    timeout=self._config.request_timeout,
                )

                if response.status_code == 404:
                    self._logger.info("Paper not found: %s", url)
                    return PaperResult(
                        session=session,
                        status=PaperStatus.NOT_FOUND,
                        message="Paper not found",
                    )

                if response.status_code in {403, 429}:
                    last_error = f"HTTP {response.status_code}"
                    self._logger.warning(
                        "Access blocked for %s on attempt %s/%s: %s",
                        url,
                        attempt,
                        self._config.max_retries,
                        last_error,
                    )
                    if attempt < self._config.max_retries:
                        time.sleep(self._config.retry_backoff_seconds * attempt)
                    continue

                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    self._logger.warning(
                        "Unexpected response for %s on attempt %s/%s: %s",
                        url,
                        attempt,
                        self._config.max_retries,
                        last_error,
                    )
                    if attempt < self._config.max_retries:
                        time.sleep(self._config.retry_backoff_seconds * attempt)
                    continue

                file_path.write_bytes(response.content)

                if is_valid_pdf(file_path):
                    self._logger.info("Downloaded PDF: %s", file_path)
                    return PaperResult(
                        session=session,
                        status=PaperStatus.DOWNLOADED,
                        file_path=file_path,
                        message="Downloaded successfully",
                    )

                last_error = "Downloaded file failed PDF validation"
                self._logger.warning("Invalid PDF received for %s", url)
                file_path.unlink(missing_ok=True)
                if attempt < self._config.max_retries:
                    time.sleep(self._config.retry_backoff_seconds * attempt)

            except requests.RequestException as exc:
                last_error = str(exc)
                self._logger.warning(
                    "Download attempt %s/%s failed for %s: %s",
                    attempt,
                    self._config.max_retries,
                    url,
                    last_error,
                )
                if attempt < self._config.max_retries:
                    time.sleep(self._config.retry_backoff_seconds * attempt)
            except OSError as exc:
                last_error = str(exc)
                self._logger.exception("File write failed for %s", file_path)
                return PaperResult(
                    session=session,
                    status=PaperStatus.FAILED,
                    message=last_error,
                )

        if file_path.exists():
            file_path.unlink(missing_ok=True)

        if last_error in {"HTTP 403", "HTTP 429"}:
            return PaperResult(
                session=session,
                status=PaperStatus.BLOCKED,
                message=last_error,
            )

        if last_error == "Downloaded file failed PDF validation":
            return PaperResult(
                session=session,
                status=PaperStatus.CORRUPTED,
                message=last_error,
            )

        return PaperResult(
            session=session,
            status=PaperStatus.FAILED,
            message=last_error or "Download failed",
        )
