"""Unit tests for gtu_pyq_downloader package."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from gtu_pyq_downloader.config import GTUPYQConfig
from gtu_pyq_downloader.models import PaperResult, PaperStatus
from gtu_pyq_downloader.services.pdf_validation import is_valid_pdf
from gtu_pyq_downloader.services.merger import PDFMergerService
from gtu_pyq_downloader.services.pipeline import GTUPYQPipeline


class TestGTUPYQConfig(unittest.TestCase):
    """Test configuration management."""

    def test_default_config(self):
        """Test that config has sensible defaults."""
        config = GTUPYQConfig()
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.request_timeout, 15.0)
        self.assertEqual(config.course_code, "BE")
        self.assertIn("W2026", config.sessions)
        self.assertIn("S2026", config.sessions)

    def test_request_headers(self):
        """Test that request headers are properly set."""
        config = GTUPYQConfig()
        headers = config.request_headers
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept", headers)
        self.assertTrue(len(headers["User-Agent"]) > 0)

    def test_subject_directory(self):
        """Test subject directory path generation."""
        config = GTUPYQConfig()
        subject_dir = config.subject_directory("3170719")
        self.assertEqual(subject_dir, Path("downloads") / "3170719")

    def test_output_pdf_path(self):
        """Test output PDF path generation."""
        config = GTUPYQConfig()
        output_path = config.output_pdf_path("3170719")
        self.assertTrue(str(output_path).endswith("PYQ (3170719).pdf"))

    def test_log_file_path(self):
        """Test log file path generation."""
        config = GTUPYQConfig()
        log_path = config.log_file_path("3170719")
        self.assertTrue(str(log_path).endswith("3170719_gtu_pyq.log"))


class TestPaperResult(unittest.TestCase):
    """Test paper result model."""

    def test_is_available_when_downloaded(self):
        """Test is_available returns True for DOWNLOADED status."""
        paper = PaperResult(
            session="W2026",
            status=PaperStatus.DOWNLOADED,
            file_path=Path("test.pdf")
        )
        self.assertTrue(paper.is_available)

    def test_is_available_when_exists(self):
        """Test is_available returns True for EXISTS status."""
        paper = PaperResult(
            session="W2026",
            status=PaperStatus.EXISTS,
            file_path=Path("test.pdf")
        )
        self.assertTrue(paper.is_available)

    def test_is_not_available_when_not_found(self):
        """Test is_available returns False for NOT_FOUND status."""
        paper = PaperResult(
            session="W2026",
            status=PaperStatus.NOT_FOUND
        )
        self.assertFalse(paper.is_available)

    def test_is_not_available_when_blocked(self):
        """Test is_available returns False for BLOCKED status."""
        paper = PaperResult(
            session="W2026",
            status=PaperStatus.BLOCKED
        )
        self.assertFalse(paper.is_available)


class TestPDFValidation(unittest.TestCase):
    """Test PDF validation."""

    def test_invalid_pdf_returns_false(self):
        """Test that non-PDF files are detected as invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_pdf = Path(tmpdir) / "fake.pdf"
            fake_pdf.write_text("This is not a PDF")
            self.assertFalse(is_valid_pdf(fake_pdf))

    def test_missing_pdf_returns_false(self):
        """Test that missing files are detected as invalid."""
        missing = Path("/nonexistent/path/test.pdf")
        self.assertFalse(is_valid_pdf(missing))

    def test_empty_pdf_returns_false(self):
        """Test that empty files are detected as invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.pdf"
            empty_file.write_bytes(b"")
            self.assertFalse(is_valid_pdf(empty_file))


class TestPDFMergerService(unittest.TestCase):
    """Test PDF merger service."""

    def test_merge_with_no_pdfs(self):
        """Test merge with empty list returns 0."""
        logger = Mock()
        merger = PDFMergerService(logger)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "output.pdf"
            result = merger.merge([], output)
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())  # Empty PDF is created

    def test_merge_skips_missing_files(self):
        """Test that merge skips files that don't exist."""
        logger = Mock()
        merger = PDFMergerService(logger)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing.pdf"
            output = Path(tmpdir) / "output.pdf"
            
            result = merger.merge([missing_file], output)
            
            # Should skip missing file and log warning
            logger.warning.assert_called()


class TestPaperStatus(unittest.TestCase):
    """Test PaperStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all expected statuses are defined."""
        self.assertEqual(PaperStatus.DOWNLOADED.value, "downloaded")
        self.assertEqual(PaperStatus.EXISTS.value, "exists")
        self.assertEqual(PaperStatus.NOT_FOUND.value, "not_found")
        self.assertEqual(PaperStatus.BLOCKED.value, "blocked")
        self.assertEqual(PaperStatus.CORRUPTED.value, "corrupted")
        self.assertEqual(PaperStatus.FAILED.value, "failed")


class TestSessionOrder(unittest.TestCase):
    """Test session ordering configuration."""

    def test_default_session_order(self):
        """Test that default session order is winter-first."""
        config = GTUPYQConfig()
        sessions = config.sessions
        # Winter 2026 should come first
        self.assertEqual(sessions[0], "W2026")
        self.assertEqual(sessions[1], "S2026")


if __name__ == "__main__":
    unittest.main()
