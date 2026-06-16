import json
from pathlib import Path
from typing import Dict, Any
from ..config import config
import logging
import hashlib

logger = logging.getLogger(__name__)


class MetadataManager:
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or config.downloads_dir

    def save_metadata(self, target_dir: Path, metadata: Dict[str, Any]):
        target_dir.mkdir(parents=True, exist_ok=True)
        p = target_dir / "metadata.json"
        with p.open("w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        logger.info("Saved metadata %s", p)
        return p

    @staticmethod
    def enhance_metadata(base_meta: Dict[str, Any], download_dir: Path) -> Dict[str, Any]:
        """Enhance metadata with URLs, file sizes, hashes, and app version."""
        import sys
        from datetime import datetime

        enhanced = dict(base_meta)

        # Add app version and timestamp if not present
        if "app_version" not in enhanced:
            enhanced["app_version"] = "2.0.0"
        if "generated_at" not in enhanced:
            enhanced["generated_at"] = datetime.utcnow().isoformat() + "Z"

        # Add file size and hash for each downloaded PDF
        enhanced["file_details"] = []
        if "downloaded" in enhanced:
            for pdf_path in enhanced["downloaded"]:
                try:
                    p = Path(pdf_path)
                    if p.exists():
                        size = p.stat().st_size
                        with p.open("rb") as fh:
                            sha256 = hashlib.sha256(fh.read()).hexdigest()
                        enhanced["file_details"].append({
                            "file": str(pdf_path),
                            "size_bytes": size,
                            "sha256": sha256,
                        })
                except Exception as exc:
                    logger.warning("Failed to compute hash for %s: %s", pdf_path, exc)

        # Add Python version
        enhanced["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        return enhanced
