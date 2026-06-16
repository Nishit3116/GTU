import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from ..config import config


def setup_logging(level: str = "INFO"):
    log_dir = config.logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s")

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(level)
    root.addHandler(ch)

    # System log (all messages)
    system_fh = RotatingFileHandler(
        log_dir / "system.log", maxBytes=5_000_000, backupCount=5
    )
    system_fh.setFormatter(formatter)
    system_fh.setLevel(logging.DEBUG)
    root.addHandler(system_fh)

    # Download log
    download_fh = RotatingFileHandler(
        log_dir / "download.log", maxBytes=5_000_000, backupCount=3
    )
    download_fh.setFormatter(formatter)
    download_logger = logging.getLogger("gtu_pyq_downloader")
    download_logger.addHandler(download_fh)

    # Merge log
    merge_fh = RotatingFileHandler(
        log_dir / "merge.log", maxBytes=5_000_000, backupCount=3
    )
    merge_fh.setFormatter(formatter)
    merge_logger = logging.getLogger("gtu_academic_engine.downloader.merger")
    merge_logger.addHandler(merge_fh)

    # Cache log
    cache_fh = RotatingFileHandler(
        log_dir / "cache.log", maxBytes=5_000_000, backupCount=3
    )
    cache_fh.setFormatter(formatter)
    cache_logger = logging.getLogger("gtu_academic_engine.cache")
    cache_logger.addHandler(cache_fh)

    # Error log (errors and warnings only)
    error_fh = RotatingFileHandler(
        log_dir / "error.log", maxBytes=5_000_000, backupCount=5
    )
    error_fh.setFormatter(formatter)
    error_fh.setLevel(logging.WARNING)
    root.addHandler(error_fh)
