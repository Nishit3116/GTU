from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PaperStatus(str, Enum):
    DOWNLOADED = "downloaded"
    EXISTS = "exists"
    NOT_FOUND = "not_found"
    BLOCKED = "blocked"
    CORRUPTED = "corrupted"
    FAILED = "failed"


@dataclass(slots=True)
class PaperResult:
    session: str
    status: PaperStatus
    file_path: Path | None = None
    message: str = ""

    @property
    def is_available(self) -> bool:
        return self.status in {PaperStatus.DOWNLOADED, PaperStatus.EXISTS}
