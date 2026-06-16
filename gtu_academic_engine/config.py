"""GTU Academic Engine V2 — centralised configuration.

All runtime paths are resolved via environment variables so the application
works identically on a developer machine and on cloud platforms (Render, etc.)
without any code change.

Supported environment variables:
    GTU_CACHE_PATH      Override the cache directory    (default: <pkg>/cache)
    GTU_DOWNLOAD_PATH   Override the downloads directory (default: <pkg>/downloads)
    GTU_LOG_PATH        Override the logs directory      (default: <pkg>/logs)
    GTU_METADATA_PATH   Override the metadata directory  (default: <pkg>/metadata)
    GTU_LOG_LEVEL       Logging level: DEBUG/INFO/WARNING/ERROR (default: INFO)
    PLAYWRIGHT_BROWSERS_PATH  Playwright binary location (set by render.yaml)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

# ── Package root (cross-platform, works on Linux / macOS / Windows) ────────────
_PKG_ROOT = Path(__file__).resolve().parent


def _env_path(var: str, default: Path) -> Path:
    """Return Path from env var, falling back to *default*."""
    raw = os.environ.get(var, "")
    return Path(raw) if raw.strip() else default


@dataclass
class Config:
    # Package root — never changes
    project_root: Path = field(default_factory=lambda: _PKG_ROOT)

    # Runtime directories — overridable via env vars
    cache_dir: Path = field(
        default_factory=lambda: _env_path("GTU_CACHE_PATH", _PKG_ROOT / "cache")
    )
    downloads_dir: Path = field(
        default_factory=lambda: _env_path("GTU_DOWNLOAD_PATH", _PKG_ROOT / "downloads")
    )
    logs_dir: Path = field(
        default_factory=lambda: _env_path("GTU_LOG_PATH", _PKG_ROOT / "logs")
    )
    metadata_dir: Path = field(
        default_factory=lambda: _env_path("GTU_METADATA_PATH", _PKG_ROOT / "metadata")
    )

    # Logging level
    log_level: str = field(
        default_factory=lambda: os.environ.get("GTU_LOG_LEVEL", "INFO").upper()
    )

    # Download behaviour
    retry_count: int = 3
    timeout_seconds: int = 10
    default_merge_order: str = "ascending"
    default_session_order: str = "winter-first"

    def ensure_dirs(self) -> None:
        """Create all required runtime directories if they do not exist.

        Called automatically on startup so the application never crashes with
        'No such file or directory' errors on a fresh environment (e.g. Render).
        Directories: cache/, downloads/, logs/, metadata/, reports/, history/
        """
        dirs = [
            self.cache_dir,
            self.downloads_dir,
            self.logs_dir,
            self.metadata_dir,
            self.project_root / "reports",
            self.project_root / "history",
        ]
        for d in dirs:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass  # best-effort; caller handles actual I/O errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_root": str(self.project_root),
            "cache_dir": str(self.cache_dir),
            "downloads_dir": str(self.downloads_dir),
            "logs_dir": str(self.logs_dir),
            "metadata_dir": str(self.metadata_dir),
            "log_level": self.log_level,
        }


# Module-level singleton — imported everywhere as `from .config import config`
config = Config()

# Auto-create runtime directories the moment this module is imported so every
# subsystem (cache, logging, downloader…) finds them ready.
config.ensure_dirs()

