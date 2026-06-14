from __future__ import annotations

import logging
import re
from pathlib import Path

from .config import GTUPYQConfig
from .models import PaperStatus
from .services.pipeline import GTUPYQPipeline, PipelineResult


SUBJECT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def configure_logging(log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("gtu_pyq_downloader")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(file_handler)

    return logger


def validate_subject_code(subject_code: str) -> str:
    cleaned = subject_code.strip()
    if not cleaned:
        raise ValueError("Subject code cannot be empty.")
    if not SUBJECT_CODE_PATTERN.fullmatch(cleaned):
        raise ValueError("Subject code can only contain letters, digits, '_' or '-'.")
    return cleaned


def print_header() -> None:
    print("====================================")
    print()
    print("GTU PYQ Downloader")
    print()
    print("====================================")
    print()


def print_footer() -> None:
    print("====================================")


def print_summary(subject_code: str, result: PipelineResult) -> None:
    papers = result.papers

    print(f"Subject Code : {subject_code}")
    print()
    print("Searching papers...")
    print()

    for paper in papers:
        if paper.status in {PaperStatus.DOWNLOADED, PaperStatus.EXISTS}:
            status_text = (
                "Downloaded" if paper.status == PaperStatus.DOWNLOADED else "Already Exists"
            )
            print(f"✅ {paper.session} {status_text}")
        elif paper.status == PaperStatus.NOT_FOUND:
            print(f"❌ {paper.session} Not Found")
        elif paper.status == PaperStatus.BLOCKED:
            print(f"⚠ {paper.session} Blocked")
        elif paper.status == PaperStatus.CORRUPTED:
            print(f"⚠ {paper.session} Corrupted")
        else:
            print(f"⚠ {paper.session} Error")

    print()
    print("====================================")
    print()
    print("Downloading Complete")
    print()
    print(f"Total Papers Found : {result.total_found}")
    print()
    print(f"Total Missing : {result.total_missing}")
    print()
    print("Merging PDFs...")
    print()

    if result.merged_files > 0:
        print("Merge Successful")
    else:
        print("Merge Skipped")

    print()
    print("Output File :")
    print()
    print(result.output_path)
    print()


def main() -> int:
    print_header()

    try:
        subject_code = validate_subject_code(input("Enter Subject Code: "))
    except EOFError:
        print("No subject code provided.")
        return 1
    except ValueError as exc:
        print(f"Invalid Subject Code: {exc}")
        return 1

    config = GTUPYQConfig()
    logger = configure_logging(config.log_file_path(subject_code))
    pipeline = GTUPYQPipeline(config, logger)

    try:
        result = pipeline.run(subject_code)
        print_summary(subject_code, result)
        print_footer()
        return 0
    except Exception as exc:
        logger.exception("Unhandled application error")
        print(f"Application error: {exc}")
        return 1
    finally:
        pipeline.close()
