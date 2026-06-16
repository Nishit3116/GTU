"""Unit tests for the GTU Academic Engine V2 collector, selector, and cache.

These tests use mock data / stubs and do NOT require internet access,
a real browser, or GTU connectivity.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ───────────────────────────────────────────────────────────────────

SAMPLE_SUBJECTS: List[Dict] = [
    {
        "subject_code": "3170719",
        "subject_name": "Theory of Computation",
        "elective_type": "Non_Elective",
        "course": "BE",
        "branch": "CE",
        "semester": "5",
        "academic_year": "2025_26",
        "course_name": "Bachelor of Engineering",
        "branch_name": "Computer Engineering",
        "semester_label": "Semester 5",
    },
    {
        "subject_code": "3150703",
        "subject_name": "Computer Networks",
        "elective_type": "Non_Elective",
        "course": "BE",
        "branch": "CE",
        "semester": "5",
        "academic_year": "2025_26",
        "course_name": "Bachelor of Engineering",
        "branch_name": "Computer Engineering",
        "semester_label": "Semester 5",
    },
    {
        "subject_code": "3170002",
        "subject_name": "Advanced Elective",
        "elective_type": "Elective",
        "course": "BE",
        "branch": "CE",
        "semester": "7",
        "academic_year": "2025_26",
        "course_name": "Bachelor of Engineering",
        "branch_name": "Computer Engineering",
        "semester_label": "Semester 7",
    },
    {
        "subject_code": "2130004",
        "subject_name": "Mathematics III",
        "elective_type": "Non_Elective",
        "course": "BE",
        "branch": "MECH",
        "semester": "3",
        "academic_year": "2025_26",
        "course_name": "Bachelor of Engineering",
        "branch_name": "Mechanical Engineering",
        "semester_label": "Semester 3",
    },
]

SAMPLE_ACADEMIC_DATA: Dict[str, Any] = {
    "database": {},
    "subjects": SAMPLE_SUBJECTS,
    "stats": {
        "success": True,
        "total_subjects": len(SAMPLE_SUBJECTS),
        "elapsed_seconds": 42.0,
    },
    "collected_at": "2026-06-14T10:00:00+00:00",
}


# ── CacheManager tests ─────────────────────────────────────────────────────────

class TestCacheManager:
    def test_save_and_load(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save("test_key", {"hello": "world"})
        loaded = cm.load("test_key")
        assert loaded == {"hello": "world"}

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        assert cm.load("nonexistent") is None

    def test_delete(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save("to_delete", [1, 2, 3])
        assert cm.load("to_delete") is not None
        cm.delete("to_delete")
        assert cm.load("to_delete") is None

    def test_atomic_save(self, tmp_path: Path) -> None:
        """Atomic save: tmp file should not remain after successful save."""
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save("atomic", {"a": 1})
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], "Temp file should be cleaned up after atomic save"

    def test_has_academic_data_false_when_empty(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        assert cm.has_academic_data() is False

    def test_has_academic_data_true_when_present(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        assert cm.has_academic_data() is True

    def test_load_academic_data(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        data = cm.load_academic_data()
        assert data is not None
        assert len(data["subjects"]) == len(SAMPLE_SUBJECTS)

    def test_get_subjects_filter_course(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        results = cm.get_subjects(course="BE")
        assert len(results) == len(SAMPLE_SUBJECTS)

    def test_get_subjects_filter_branch(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        results = cm.get_subjects(branch="CE")
        assert all(s["branch"] == "CE" for s in results)
        assert len(results) == 3

    def test_get_subjects_filter_semester(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        results = cm.get_subjects(semester="5")
        assert all(str(s["semester"]) == "5" for s in results)
        assert len(results) == 2

    def test_get_academic_data_info(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        info = cm.get_academic_data_info()
        assert info["exists"] is True
        assert info["total_subjects"] == len(SAMPLE_SUBJECTS)

    def test_stats(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save("courses", [{"id": "BE", "name": "Bachelor of Engineering"}])
        stats = cm.stats()
        assert stats["files"] >= 1
        assert stats["size_bytes"] > 0


# ── search_subjects tests ──────────────────────────────────────────────────────

class TestSearchSubjects:
    def _cm(self, tmp_path: Path):
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        return cm

    def test_search_exact_code(self, tmp_path: Path) -> None:
        cm = self._cm(tmp_path)
        results = cm.search_subjects("3170719")
        assert results
        assert results[0]["subject_code"] == "3170719"

    def test_search_name_partial(self, tmp_path: Path) -> None:
        cm = self._cm(tmp_path)
        results = cm.search_subjects("Theory")
        assert any(r["subject_code"] == "3170719" for r in results)

    def test_search_no_match(self, tmp_path: Path) -> None:
        cm = self._cm(tmp_path)
        results = cm.search_subjects("XXXXXXX_not_exist")
        assert results == []

    def test_search_empty_query(self, tmp_path: Path) -> None:
        cm = self._cm(tmp_path)
        results = cm.search_subjects("")
        assert len(results) > 0  # returns all up to top_n

    def test_search_top_n(self, tmp_path: Path) -> None:
        cm = self._cm(tmp_path)
        results = cm.search_subjects("", top_n=2)
        assert len(results) <= 2


# ── SubjectSelector tests ──────────────────────────────────────────────────────

class TestSubjectSelector:
    def _make_selector(self, tmp_path: Path):
        from gtu_academic_engine.cache.cache_manager import CacheManager
        from gtu_academic_engine.selector.subject_selector import SubjectSelector
        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        return SubjectSelector(cm)

    def test_load_succeeds_when_data_present(self, tmp_path: Path) -> None:
        sel = self._make_selector(tmp_path)
        assert sel._load() is True

    def test_load_fails_when_no_data(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        from gtu_academic_engine.selector.subject_selector import SubjectSelector
        cm = CacheManager(cache_dir=tmp_path)
        sel = SubjectSelector(cm)
        assert sel._load() is False

    def test_fuzzy_search(self, tmp_path: Path) -> None:
        from gtu_academic_engine.selector.subject_selector import _search_subjects
        results = _search_subjects(SAMPLE_SUBJECTS, "Computation")
        assert results
        assert results[0]["subject_code"] == "3170719"

    def test_fuzzy_search_by_code(self, tmp_path: Path) -> None:
        from gtu_academic_engine.selector.subject_selector import _search_subjects
        results = _search_subjects(SAMPLE_SUBJECTS, "3150703")
        assert results
        assert results[0]["subject_code"] == "3150703"

    def test_fuzzy_search_no_match(self, tmp_path: Path) -> None:
        from gtu_academic_engine.selector.subject_selector import _search_subjects
        results = _search_subjects(SAMPLE_SUBJECTS, "ZZZZZZ")
        assert results == []

    def test_run_returns_none_without_data(self, tmp_path: Path, capsys) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        from gtu_academic_engine.selector.subject_selector import SubjectSelector
        cm = CacheManager(cache_dir=tmp_path)
        sel = SubjectSelector(cm)
        result = sel.run()
        assert result is None
        captured = capsys.readouterr()
        assert "No academic data" in captured.out


# ── Exporter tests ─────────────────────────────────────────────────────────────

class TestExporter:
    def test_export_csv(self, tmp_path: Path) -> None:
        from gtu_academic_engine.collector.exporter import export_csv
        dest = tmp_path / "out.csv"
        path = export_csv(SAMPLE_SUBJECTS, dest)
        assert path.exists()
        content = path.read_text(encoding="utf-8-sig")
        assert "subject_code" in content
        assert "3170719" in content

    def test_export_csv_empty(self, tmp_path: Path) -> None:
        from gtu_academic_engine.collector.exporter import export_csv
        dest = tmp_path / "empty.csv"
        export_csv([], dest)
        assert dest.exists()

    def test_export_report(self, tmp_path: Path) -> None:
        from gtu_academic_engine.collector.exporter import export_report
        dest = tmp_path / "report.txt"
        export_report(SAMPLE_ACADEMIC_DATA, dest)
        assert dest.exists()
        content = dest.read_text()
        assert "GTU Academic Data" in content
        assert "Total Subjects" in content

    def test_export_all_creates_files(self, tmp_path: Path) -> None:
        from gtu_academic_engine.collector.exporter import export_all
        paths = export_all(SAMPLE_ACADEMIC_DATA, tmp_path / "exports")
        assert "csv" in paths
        assert "report" in paths
        assert paths["csv"].exists()
        assert paths["report"].exists()

    def test_export_xlsx(self, tmp_path: Path) -> None:
        openpyxl = pytest.importorskip("openpyxl")
        from gtu_academic_engine.collector.exporter import export_xlsx
        dest = tmp_path / "out.xlsx"
        export_xlsx(SAMPLE_SUBJECTS, dest)
        assert dest.exists()
        assert dest.stat().st_size > 100


# ── AcademicCollector mock test ────────────────────────────────────────────────

class TestAcademicCollector:
    def test_collector_saves_to_cache(self, tmp_path: Path) -> None:
        """Collector should save to cache even when provider returns minimal data."""
        from gtu_academic_engine.collector.academic_collector import AcademicCollector

        fake_result = {
            "BE": {
                "_meta": {"id": "BE", "name": "Bachelor of Engineering"},
                "_branches": {
                    "CE": {
                        "_meta": {"id": "CE", "name": "Computer Engineering"},
                        "_semesters": {
                            "5": {
                                "_meta": {"value": "5", "text": "Semester 5"},
                                "_electives": {
                                    "Non_Elective": [
                                        {
                                            "subject_code": "3170719",
                                            "subject_name": "Theory of Computation",
                                            "elective_type": "Non_Elective",
                                            "course": "BE",
                                            "branch": "CE",
                                            "semester": "5",
                                        }
                                    ]
                                },
                            }
                        },
                    }
                },
            }
        }

        collector = AcademicCollector(cache_dir=tmp_path)

        with patch("gtu_academic_engine.provider.aspx_provider.ASPXProvider") as MockProvider:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.collect_all = MagicMock(return_value=fake_result)
            MockProvider.return_value = instance

            result = collector.run()

        assert result["stats"]["success"] is True
        assert len(result["subjects"]) == 1
        assert result["subjects"][0]["subject_code"] == "3170719"

        # Check file was saved
        saved = tmp_path / "gtu_academic_data.json"
        assert saved.exists()
        data = json.loads(saved.read_text())
        assert data["subjects"][0]["subject_code"] == "3170719"


class TestSyllabusDownloaderDirectURL:
    def test_download_uses_direct_url(self, tmp_path: Path) -> None:
        from gtu_academic_engine.downloader.syllabus_downloader import SyllabusDownloader
        from unittest.mock import patch, MagicMock

        subject = {
            "subject_code": "3170719",
            "subject_name": "Theory of Computation",
            "course": "BE",
            "branch": "CE",
            "semester": "5",
            "academic_year": "2024-25",
            "elective_type": "Non_Elective",
            "syllabus_pdf_url": "https://custom-s3-path.amazonaws.com/Syallbus/3170719.pdf",
        }

        dl = SyllabusDownloader(base_dir=tmp_path)

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"%PDF-1.4 mock pdf data"
            mock_get.return_value = mock_response

            saved_path = dl.download(subject)

            assert saved_path is not None
            assert saved_path.exists()
            assert saved_path.name == "syllabus.pdf"
            mock_get.assert_called_once_with(
                "https://custom-s3-path.amazonaws.com/Syallbus/3170719.pdf",
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Referer": "https://gtu.ac.in/syllabus/syllabus.aspx",
                }
            )


class TestSelectorFlowOrder:
    def test_selector_flow_order(self, tmp_path: Path) -> None:
        from gtu_academic_engine.cache.cache_manager import CacheManager
        from gtu_academic_engine.selector.subject_selector import SubjectSelector
        from unittest.mock import patch

        cm = CacheManager(cache_dir=tmp_path)
        cm.save_academic_data(SAMPLE_ACADEMIC_DATA)
        sel = SubjectSelector(cm)

        # Mock select methods to check execution order
        with patch.object(sel, "_select_level") as mock_select_level, \
             patch.object(sel, "_select_plain") as mock_select_plain, \
             patch.object(sel, "_select_subject") as mock_select_subject:

            mock_select_level.side_effect = ["BE", "CE", "5", "Non_Elective"]
            mock_select_plain.return_value = "2025_26"
            mock_select_subject.return_value = SAMPLE_SUBJECTS[0]

            res = sel.run()

            assert res == SAMPLE_SUBJECTS[0]
            
            # Verify the steps order:
            # 1. course
            # 2. branch
            # 3. semester
            # 4. academic_year (via plain)
            # 5. elective_type
            calls = mock_select_level.call_args_list
            assert len(calls) == 4
            assert calls[0][0][1] == "course"
            assert calls[1][0][1] == "branch"
            assert calls[2][0][1] == "semester"
            
            mock_select_plain.assert_called_once()
            assert mock_select_plain.call_args[0][0] == ["2025_26"]
            
            assert calls[3][0][1] == "elective_type"

