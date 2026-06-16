from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def generate_report(target_dir: Path, meta: Dict[str, Any]) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    p = target_dir / "report.txt"
    lines = []
    lines.append(f"Subject: {meta.get('subject_name','-')}")
    lines.append(f"Subject Code: {meta.get('subject_code','-')}")
    lines.append(f"Course: {meta.get('course','-')}")
    lines.append(f"Branch: {meta.get('branch','-')}")
    lines.append(f"Downloaded Papers: {len(meta.get('downloaded',[]))}")
    lines.append(f"Missing Papers: {len(meta.get('missing',[]))}")
    lines.append(f"Merge Order: {meta.get('merge_order','-')}")
    lines.append(f"Session Order: {meta.get('session_order','-')}")
    with p.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    logger.info("Wrote report %s", p)
    return p
