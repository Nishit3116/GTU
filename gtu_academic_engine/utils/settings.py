import json
from pathlib import Path
from typing import Dict, Any
from ..config import config


class SettingsManager:
    def __init__(self, settings_file: Path | None = None):
        self.settings_file = settings_file or (config.project_root / "settings.json")
        self.defaults = {
            "retry_count": 3,
            "timeout_seconds": 15,
            "download_path": str(config.downloads_dir),
            "cache_path": str(config.cache_dir),
            "logs_path": str(config.logs_dir),
            "auto_merge": True,
            "auto_refresh_cache": False,
            "default_merge_order": "ascending",
            "default_session_order": "winter-first",
            "progress_bar": True,
            "logging_level": "INFO",
            "parallel_downloads": 1,
        }
        self.settings = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.settings_file.exists():
            try:
                with self.settings_file.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                return dict(self.defaults)
        return dict(self.defaults)

    def save(self) -> None:
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        with self.settings_file.open("w", encoding="utf-8") as fh:
            json.dump(self.settings, fh, indent=2)

    def get(self, key: str, default=None):
        return self.settings.get(key, default if default is not None else self.defaults.get(key))

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save()

    def reset(self) -> None:
        self.settings = dict(self.defaults)
        self.save()

    def display(self):
        for k, v in self.settings.items():
            print(f"  {k}: {v}")
