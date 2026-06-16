import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import config

logger = logging.getLogger(__name__)

# Name of the single-source-of-truth academic database cache file
_ACADEMIC_DATA_FILE = "gtu_academic_data"


class CacheManager:
    """Manages all JSON cache files under the cache/ directory.

    Standard caches (per-file):
        courses, branches, academic_years, semesters, electives, subjects,
        last_refresh

    Master academic database:
        gtu_academic_data.json — hierarchical + flat subjects list written by
        AcademicCollector.  Access via load_academic_data() / save_academic_data().
    """

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or config.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _path(self, name: str) -> Path:
        return self.cache_dir / f"{name}.json"

    # ── Standard CRUD ─────────────────────────────────────────────────────────

    def save(self, name: str, data: Any) -> None:
        """Atomically save data to a named cache file."""
        p = self._path(name)
        tmp = p.with_suffix(".json.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            tmp.replace(p)
            logger.info("Saved cache %s", p)
        except Exception as exc:
            logger.error("Failed to save cache %s: %s", name, exc)
            tmp.unlink(missing_ok=True)
            raise

    def load(self, name: str) -> Any:
        """Load a named cache file, returning None if it does not exist."""
        p = self._path(name)
        if not p.exists():
            logger.debug("Cache %s not found", p)
            return None
        try:
            with p.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            logger.info("Loaded cache %s", p)
            return data
        except Exception as exc:
            logger.warning("Failed to read cache %s: %s", name, exc)
            return None

    def delete(self, name: str) -> None:
        p = self._path(name)
        if p.exists():
            p.unlink()
            logger.info("Deleted cache %s", p)

    def refresh(self):
        logger.info("Refreshing all caches: TODO implement")

    def list_caches(self) -> list[str]:
        return [p.stem for p in self.cache_dir.glob("*.json")]

    def export(self, name: str, dest: Path) -> None:
        p = self._path(name)
        if not p.exists():
            raise FileNotFoundError(p)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        logger.info("Exported cache %s -> %s", p, dest)

    def import_cache(self, src: Path, name: str) -> None:
        dest = self._path(name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        logger.info("Imported cache %s -> %s", src, dest)

    def stats(self) -> Dict[str, Any]:
        total_size = 0
        counts: Dict[str, Any] = {}
        for p in self.cache_dir.glob("*.json"):
            total_size += p.stat().st_size
            counts[p.stem] = None
        for name in ["courses", "branches", "subjects"]:
            data = self.load(name)
            counts[name] = (
                len(data) if isinstance(data, list)
                else (len(data.keys()) if isinstance(data, dict) else 0)
            )
        return {
            "files": len(list(self.cache_dir.glob("*.json"))),
            "size_bytes": total_size,
            "counts": counts,
        }

    # ── Academic Database ─────────────────────────────────────────────────────

    def load_academic_data(self) -> Optional[Dict[str, Any]]:
        """Load the master academic database (gtu_academic_data.json).

        Returns the full result dict from AcademicCollector, or None if absent.
        Keys: "database", "subjects", "stats", "collected_at"
        """
        return self.load(_ACADEMIC_DATA_FILE)

    def save_academic_data(self, data: Dict[str, Any]) -> None:
        """Save the master academic database atomically."""
        self.save(_ACADEMIC_DATA_FILE, data)

    def has_academic_data(self) -> bool:
        """Return True if gtu_academic_data.json exists and has subjects."""
        data = self.load_academic_data()
        if not data:
            return False
        return bool(data.get("subjects"))

    def get_subjects(
        self,
        course: Optional[str] = None,
        branch: Optional[str] = None,
        year: Optional[str] = None,
        semester: Optional[str] = None,
        elective_type: Optional[str] = None,
    ) -> List[Dict]:
        """Query flat subjects list with optional filters.

        All parameters are optional; omit any to skip that filter.
        """
        data = self.load_academic_data()
        if not data:
            return []

        subjects: List[Dict] = data.get("subjects", [])

        filters = [
            ("course", course),
            ("branch", branch),
            ("academic_year", year),
            ("elective_type", elective_type),
        ]
        for key, val in filters:
            if val is not None:
                subjects = [s for s in subjects if str(s.get(key, "")) == str(val)]

        if semester is not None:
            subjects = [
                s for s in subjects
                if str(s.get("semester", "")) == str(semester)
            ]

        return subjects

    def search_subjects(self, query: str, top_n: int = 30) -> List[Dict]:
        """Fuzzy-search subjects by name or subject code.

        Args:
            query: Search string (matches subject_name and subject_code)
            top_n: Maximum number of results to return

        Returns:
            List of subject dicts sorted by relevance (best match first).
        """
        import re

        data = self.load_academic_data()
        if not data:
            return []

        subjects: List[Dict] = data.get("subjects", [])

        def normalize(text: str) -> str:
            return re.sub(r"[^a-z0-9]", "", text.lower())

        def score(query_n: str, text_n: str) -> int:
            if query_n == text_n:
                return 100
            if query_n in text_n:
                return 80
            
            from difflib import SequenceMatcher
            ratio = SequenceMatcher(None, query_n, text_n).ratio()
            if ratio >= 0.6:
                return int(ratio * 90)
                
            idx = 0
            for ch in query_n:
                pos = text_n.find(ch, idx)
                if pos == -1:
                    return 0
                idx = pos + 1
            return max(10, 60 - (len(text_n) - len(query_n)))

        q = query.strip()
        
        # Check if there is a subject code (5 to 10 digits) in the query
        code_match = re.search(r"\b\d{5,10}\b", q)
        extracted_code = code_match.group(0) if code_match else None
        
        # Clean text query by removing the extracted code
        q_text = q
        if extracted_code:
            q_text = q.replace(extracted_code, "").strip()
            
        q_text_norm = normalize(q_text)
        
        if not extracted_code and not q_text_norm:
            return subjects[:top_n]

        scored = []
        for s in subjects:
            code = s.get("subject_code", "")
            name = s.get("subject_name", "")
            
            # Code scoring
            code_score = 0
            if extracted_code:
                if extracted_code == code:
                    code_score = 100
                elif extracted_code in code:
                    code_score = 60
            else:
                if q == code:
                    code_score = 100
                elif q in code:
                    code_score = 50
            
            # Name scoring
            name_score = 0
            if q_text_norm:
                name_norm = normalize(name)
                if q_text_norm == name_norm:
                    name_score = 100
                elif q_text_norm in name_norm or name_norm in q_text_norm:
                    name_score = 80
                else:
                    name_score = score(q_text_norm, name_norm)
            
            best = max(code_score, name_score)
            if best > 0:
                scored.append((best, s))

        scored.sort(key=lambda x: -x[0])
        return [s for _, s in scored[:top_n]]

    def get_academic_data_info(self) -> Dict[str, Any]:
        """Return a summary dict about the academic database."""
        data = self.load_academic_data()
        if not data:
            return {"exists": False}

        subjects = data.get("subjects", [])
        stats = data.get("stats", {})
        return {
            "exists": True,
            "total_subjects": len(subjects),
            "collected_at": data.get("collected_at", "?"),
            "courses": len({s.get("course") for s in subjects}),
            "branches": len({s.get("branch") for s in subjects}),
            "elapsed_seconds": stats.get("elapsed_seconds"),
        }
