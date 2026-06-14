from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ..config import GTUPYQConfig
from ..models import PaperResult
from .downloader import GTUPYQDownloader
from .merger import PDFMergerService


@dataclass(slots=True)
class PipelineResult:
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
    def __init__(self, config: GTUPYQConfig, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger
        self._downloader = GTUPYQDownloader(config, logger)
        self._merger = PDFMergerService(logger)

    def close(self) -> None:
        self._downloader.close()

    def run(self, subject_code: str) -> PipelineResult:
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

        return PipelineResult(
            subject_code=subject_code,
            papers=papers,
            output_path=output_path,
            merged_files=merged_files,
        )
