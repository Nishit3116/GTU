"""GTU Academic Data Collector.

Orchestrates a full collection run using ASPXProvider:
  Course → Branch → Semester → Elective → Subjects

Results are saved as a flat subject list alongside a hierarchical nested dict.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_COLLECTOR_LOG = "collector.log"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AcademicCollector:
    """Drives ASPXProvider to collect the entire GTU academic hierarchy.

    Usage::

        collector = AcademicCollector(headless=True)
        result = collector.run(progress_callback=my_callback)
        # result contains {"database": {...}, "subjects": [...], "stats": {...}}
    """

    def __init__(
        self,
        headless: bool = True,
        debug: bool = False,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self._headless = headless
        self._debug = debug
        self._cache_dir = cache_dir or self._default_cache_dir()
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Configure a dedicated collector log file
        log_path = self._cache_dir.parent / "logs" / _COLLECTOR_LOG
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(fh)

    @staticmethod
    def _default_cache_dir() -> Path:
        try:
            from gtu_academic_engine.config import config
            return config.cache_dir
        except Exception:
            return Path("cache")

    def run(
        self,
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> Dict[str, Any]:
        """Run the full collection.

        Args:
            progress_callback: Optional callable invoked after each leaf node.
                Receives a dict with keys:
                    course, branch, semester, elective, subjects_found, total_so_far

        Returns:
            dict with:
                "database"  — hierarchical nested structure
                "subjects"  — flat list of all subject dicts
                "stats"     — counts and timing
        """
        from gtu_academic_engine.provider.aspx_provider import ASPXProvider

        start_time = time.monotonic()
        logger.info("=== AcademicCollector run started ===")

        # Internal callback wrapper for console progress
        _counter = {"n": 0}

        def _internal_cb(info: Dict) -> None:
            _counter["n"] += 1
            year_info = f" year={info.get('academic_year', '')}" if info.get('academic_year') else ""
            print(
                f"\r  [{_counter['n']:4d}] {info['course']}/{info['branch']} "
                f"sem={info['semester']}{year_info} {info['elective']} "
                f"→ {info['subjects_found']} subjects "
                f"(total={info['total_so_far']})",
                end="",
                flush=True,
            )
            if progress_callback:
                progress_callback(info)

        database: Dict[str, Any] = {}
        flat_subjects: List[Dict] = []
        error_count = 0

        try:
            with ASPXProvider(
                headless=self._headless,
                slow_mo_ms=200 if self._debug else 0,
            ) as provider:
                raw_database = provider.collect_all(progress_callback=_internal_cb)
        except Exception as exc:
            logger.error("Provider collection failed: %s", exc, exc_info=True)
            return {
                "database": {},
                "subjects": [],
                "stats": {"error": str(exc), "success": False},
            }

        print()  # newline after progress line

        # Flatten subjects from hierarchical database
        for cid, course_data in raw_database.items():
            course_name = course_data.get("_meta", {}).get("name", cid)
            for bid, branch_data in course_data.get("_branches", {}).items():
                branch_name = branch_data.get("_meta", {}).get("name", bid)
                for sem_val, sem_data in branch_data.get("_semesters", {}).items():
                    sem_text = sem_data.get("_meta", {}).get("text", sem_val)
                    for elective, subjects in sem_data.get("_electives", {}).items():
                        for subj in subjects:
                            flat_subj = {
                                **subj,
                                "course_name": course_name,
                                "branch_name": branch_name,
                                "semester_label": sem_text,
                            }
                            flat_subjects.append(flat_subj)

        elapsed = time.monotonic() - start_time
        stats = {
            "success": True,
            "total_subjects": len(flat_subjects),
            "courses": len(raw_database),
            "elapsed_seconds": round(elapsed, 2),
            "collected_at": _utc_now(),
            "errors": error_count,
        }

        logger.info(
            "Collection complete: %d subjects in %.1fs",
            len(flat_subjects), elapsed,
        )

        result = {
            "database": raw_database,
            "subjects": flat_subjects,
            "stats": stats,
            "collected_at": _utc_now(),
        }

        # Auto-save to cache
        self._save_to_cache(result)

        return result

    def _save_to_cache(self, result: Dict[str, Any]) -> None:
        """Save results to gtu_academic_data.json atomically."""
        target = self._cache_dir / "gtu_academic_data.json"
        tmp = target.with_suffix(".json.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2, ensure_ascii=False)
            tmp.replace(target)
            logger.info("Saved academic data to %s", target)
        except Exception as exc:
            logger.error("Failed to save academic data: %s", exc)
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    @staticmethod
    def print_summary(result: Dict[str, Any]) -> None:
        """Print a human-readable collection summary."""
        stats = result.get("stats", {})
        subjects = result.get("subjects", [])
        courses = set(s.get("course", "") for s in subjects)
        branches = set(s.get("branch", "") for s in subjects)

        print("\n" + "=" * 50)
        print("GTU Academic Data — Collection Summary")
        print("=" * 50)
        print(f"  Status          : {'✓ Success' if stats.get('success') else '✗ Failed'}")
        print(f"  Courses         : {len(courses)}")
        print(f"  Branches        : {len(branches)}")
        print(f"  Total Subjects  : {stats.get('total_subjects', len(subjects))}")
        print(f"  Elapsed         : {stats.get('elapsed_seconds', '?')}s")
        print(f"  Collected At    : {stats.get('collected_at', '?')}")
        if stats.get("errors"):
            print(f"  Errors          : {stats['errors']}")
        print("=" * 50)
