from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class Config:
    project_root: Path = Path(__file__).resolve().parent
    cache_dir: Path = project_root / "cache"
    downloads_dir: Path = project_root / "downloads"
    logs_dir: Path = project_root / "logs"
    retry_count: int = 3
    timeout_seconds: int = 10
    default_merge_order: str = "ascending"
    default_session_order: str = "winter-first"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cache_dir": str(self.cache_dir),
            "downloads_dir": str(self.downloads_dir),
            "logs_dir": str(self.logs_dir),
        }

config = Config()
