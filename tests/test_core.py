import unittest
from pathlib import Path
from gtu_academic_engine.downloader.session_generator import generate_sessions
from gtu_academic_engine.downloader.url_generator import generate_urls
from gtu_academic_engine.downloader.validator import is_valid_pdf
from gtu_academic_engine.cache.cache_manager import CacheManager
from gtu_academic_engine.utils.settings import SettingsManager
from gtu_academic_engine.utils.file_utils import standardize_pdf_name, standardize_merged_name


class TestSessionGenerator(unittest.TestCase):
    def test_winter_first_order(self):
        sessions = generate_sessions(2021, 2023, order="winter-first")
        expected = ["W2023", "S2023", "W2022", "S2022", "W2021", "S2021"]
        self.assertEqual(sessions, expected)

    def test_summer_first_order(self):
        sessions = generate_sessions(2021, 2023, order="summer-first")
        expected = ["S2023", "W2023", "S2022", "W2022", "S2021", "W2021"]
        self.assertEqual(sessions, expected)

    def test_single_year(self):
        sessions = generate_sessions(2021, 2021, order="winter-first")
        self.assertEqual(len(sessions), 2)
        self.assertIn("W2021", sessions)
        self.assertIn("S2021", sessions)


class TestURLGenerator(unittest.TestCase):
    def test_url_generation(self):
        sessions = ["W2026", "S2026"]
        urls = generate_urls(sessions, "BE", "3170719")
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0], "https://gtu.ac.in/uploads/W2026/BE/3170719.pdf")
        self.assertEqual(urls[1], "https://gtu.ac.in/uploads/S2026/BE/3170719.pdf")


class TestFileNaming(unittest.TestCase):
    def test_pdf_naming(self):
        name = standardize_pdf_name("W2026", "3170719")
        self.assertEqual(name, "W2026_3170719.pdf")

    def test_merged_naming(self):
        name = standardize_merged_name("3170719", 2021, 2026)
        self.assertEqual(name, "3170719_PYQ_2026_2021.pdf")


class TestCacheManager(unittest.TestCase):
    def test_save_load(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(Path(tmpdir))
            test_data = {"id": "BE", "name": "Engineering"}
            cache.save("test", test_data)
            loaded = cache.load("test")
            self.assertEqual(loaded, test_data)

    def test_list_caches(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(Path(tmpdir))
            cache.save("courses", [])
            cache.save("branches", [])
            caches = cache.list_caches()
            self.assertIn("courses", caches)
            self.assertIn("branches", caches)


class TestSettings(unittest.TestCase):
    def test_default_settings(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = SettingsManager(Path(tmpdir) / "settings.json")
            self.assertEqual(settings.get("retry_count"), 3)
            self.assertEqual(settings.get("timeout_seconds"), 15)

    def test_set_get(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = SettingsManager(Path(tmpdir) / "settings.json")
            settings.set("retry_count", 5)
            self.assertEqual(settings.get("retry_count"), 5)


if __name__ == "__main__":
    unittest.main()
