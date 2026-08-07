import json
from pathlib import Path
from typing import Dict, Any, List
from ..config import config


class HistoryManager:
    def __init__(self, history_file: Path | None = None):
        self.history_file = history_file or (config.project_root / "history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: Dict[str, Any]) -> None:
        data = self._read()
        data.append(entry)
        with self.history_file.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    def list(self) -> List[Dict[str, Any]]:
        return self._read()

    def _read(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        with self.history_file.open("r", encoding="utf-8") as fh:
            try:
                return json.load(fh)
            except Exception:
                return []

    def export_csv(self, dest: Path) -> Path:
        import csv
        entries = self.list()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", newline='', encoding="utf-8") as fh:
            if not entries:
                fh.write("")
                return dest
            keys = list(entries[0].keys())
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            for e in entries:
                writer.writerow(e)
        return dest
