"""GTU PYQ download and merge pipeline orchestrator.

Coordinates the overall workflow: download papers for all sessions, then 
merge the valid ones into a single PDF in the specified order.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ..config import GTUPYQConfig
from ..models import PaperResult
from .downloader import GTUPYQDownloader
from .merger import PDFMergerService

# optional history manager from v2 scaffold
try:
    from gtu_academic_engine.utils.history_manager import HistoryManager
except Exception:
    HistoryManager = None


@dataclass(slots=True)
class PipelineResult:
    """Result of a download and merge pipeline execution.
    
    Attributes:
        subject_code: The GTU subject code that was processed
        papers: List of PaperResult objects for each session
        output_path: Path to the final merged PDF file
        merged_files: Number of PDFs successfully merged
    """
    subject_code: str
    papers: list[PaperResult]
    output_path: Path
    merged_files: int

    @property
    def total_found(self) -> int:
        return sum(1 for paper in self.papers if paper.is_available)

    @property
    def total_missing(self) -> int:
        return sum(1 for paper in self.papers if not paper.is_available)


class GTUPYQPipeline:
    """Orchestrates the download and merge pipeline for GTU PYQ papers.
    
    Coordinates:
    1. Downloading papers for all configured sessions
    2. Merging valid PDFs in the configured session order
    3. Recording download history (best-effort)
    """
    
    def __init__(self, config: GTUPYQConfig, logger: logging.Logger) -> None:
        """Initialize the pipeline with configuration and logger.
        
        Args:
            config: GTUPYQConfig instance with sessions and paths
            logger: Logger instance for operation tracking
        """
        self._config = config
        self._logger = logger
        self._downloader = GTUPYQDownloader(config, logger)
        self._merger = PDFMergerService(logger)

    def close(self) -> None:
        """Close and cleanup resources (HTTP session, connections, etc.)."""
        self._downloader.close()

    def run(self, subject_code: str) -> PipelineResult:
        """Run the complete download and merge pipeline.
        
        Args:
            subject_code: GTU subject code to download papers for
            
        Returns:
            PipelineResult with download status, file paths, and merge results
        """
        papers: list[PaperResult] = []

        for session in self._config.sessions:
            result = self._downloader.fetch_paper(subject_code, session)
            papers.append(result)

        available_paths = [
            paper.file_path
            for paper in papers
            if paper.is_available and paper.file_path is not None
        ]

        output_path = self._config.output_pdf_path(subject_code)
        merged_files = 0

        if available_paths:
            merged_files = self._merger.merge(available_paths, output_path)

        # record history (best-effort)
        try:
            if HistoryManager is not None:
                hm = HistoryManager()
                hm.append({
                    "subject": subject_code,
                    "downloaded": sum(1 for p in papers if p.is_available),
                    "missing": sum(1 for p in papers if not p.is_available),
                    "output_path": str(output_path),
                })
        except Exception:
            pass

        return PipelineResult(
            subject_code=subject_code,
            papers=papers,
            output_path=output_path,
            merged_files=merged_files,
        )
