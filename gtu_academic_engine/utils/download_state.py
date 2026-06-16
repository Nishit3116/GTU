import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class DownloadState:
    """Tracks download progress for resume support."""

    def __init__(self, subject_code: str, download_dir: Path):
        self.subject_code = subject_code
        self.download_dir = download_dir
        self.state_file = download_dir / f".{subject_code}_state.json"
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with self.state_file.open("r") as fh:
                    return json.load(fh)
            except Exception:
                return self._init_state()
        return self._init_state()

    def _init_state(self) -> Dict[str, Any]:
        return {
            "subject_code": self.subject_code,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed": [],
            "failed": [],
            "skipped": [],
            "total_sessions": 0,
        }

    def mark_completed(self, session: str) -> None:
        if session not in self.data["completed"]:
            self.data["completed"].append(session)
        self.save()

    def mark_failed(self, session: str) -> None:
        if session not in self.data["failed"]:
            self.data["failed"].append(session)
        self.save()

    def mark_skipped(self, session: str) -> None:
        if session not in self.data["skipped"]:
            self.data["skipped"].append(session)
        self.save()

    def is_complete(self, session: str) -> bool:
        return session in self.data["completed"]

    def is_failed(self, session: str) -> bool:
        return session in self.data["failed"]

    def pending_sessions(self, all_sessions: list) -> list:
        done = set(self.data["completed"]) | set(self.data["skipped"])
        return [s for s in all_sessions if s not in done]

    def save(self) -> None:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w") as fh:
            json.dump(self.data, fh, indent=2)

    def clear(self) -> None:
        if self.state_file.exists():
            self.state_file.unlink()
        self.data = self._init_state()

    def is_incomplete(self) -> bool:
        """Check if download was previously started but not finished."""
        return self.state_file.exists() and (self.data.get("completed") or self.data.get("failed"))
