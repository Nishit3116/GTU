from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_SESSIONS = [
    "W2026",
    "S2026",
    "W2025",
    "S2025",
    "W2024",
    "S2024",
    "W2023",
    "S2023",
    "W2022",
    "S2022",
    "W2021",
    "S2021",
]


@dataclass(slots=True)
class GTUPYQConfig:
    base_url: str = "https://gtu.ac.in/uploads/{session}/BE/{subject_code}.pdf"
    bootstrap_url: str = "https://gtu.ac.in/Default.aspx"
    repository_url: str = "https://gtu.ac.in/Download1.aspx"
    course_code: str = "BE"
    sessions: list[str] = field(default_factory=lambda: list(DEFAULT_SESSIONS))
    downloads_dir: Path = field(default_factory=lambda: Path("downloads"))
    logs_dir: Path = field(default_factory=lambda: Path("logs"))
    request_timeout: float = 15.0
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    user_agent: str = "Mozilla/5.0 (compatible; GTUPYQDownloader/1.0)"

    @property
    def request_headers(self) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://gtu.ac.in/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def subject_directory(self, subject_code: str) -> Path:
        return self.downloads_dir / subject_code

    def output_pdf_path(self, subject_code: str) -> Path:
        return self.subject_directory(subject_code) / (
            f"PYQ ({subject_code}).pdf"
        )

    def log_file_path(self, subject_code: str) -> Path:
        return self.logs_dir / f"{subject_code}_gtu_pyq.log"
