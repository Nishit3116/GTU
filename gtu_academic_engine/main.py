"""GTU Academic Engine V2 - Main Application Entry Point.

Provides a comprehensive menu-driven interface for:
- Downloading Previous Year Papers  (selector-based, no manual subject code)
- Downloading Syllabus              (selector-based, real download)
- Combined PYQ + Syllabus download
- Collecting / Refreshing GTU Academic Data  (Playwright browser automation)
- Download history tracking
- Cache management
- Settings configuration
"""

from pathlib import Path
import logging
import time
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .utils.logging_config import setup_logging
from .cache.cache_manager import CacheManager
from .utils.history_manager import HistoryManager
from .utils.settings import SettingsManager
from .config import config


logger = logging.getLogger(__name__)


# ── Connectivity helpers ───────────────────────────────────────────────────────

def check_internet(timeout: float = 3.0) -> bool:
    import requests
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False


def check_gtu(timeout: float = 5.0) -> bool:
    import requests
    try:
        requests.get("https://gtu.ac.in/", timeout=timeout)
        return True
    except Exception:
        return False


# ── UI helpers ─────────────────────────────────────────────────────────────────

def _header(title: str = "GTU Academic Engine V2") -> None:
    w = max(len(title) + 4, 50)
    print("\n" + "=" * w)
    pad = (w - len(title)) // 2
    print(" " * pad + title)
    print("=" * w)


def _divider(w: int = 50) -> None:
    print("-" * w)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Startup ────────────────────────────────────────────────────────────────────

def startup_checks() -> tuple:
    _header()
    print("  Loading configuration...")
    cache = CacheManager()

    print("  Checking internet...", end="", flush=True)
    internet_ok = check_internet()
    print(" OK" if internet_ok else " OFFLINE")

    print("  Checking GTU...", end="", flush=True)
    gtu_ok = check_gtu()
    print(" OK" if gtu_ok else " UNREACHABLE")

    if not internet_ok or not gtu_ok:
        print("\n  WARNING: GTU unreachable. Cached data will be used where available.")
    else:
        print("\n  Ready to proceed.")

    # Show academic data status
    info = cache.get_academic_data_info()
    if info.get("exists"):
        print("  Academic database: {} subjects  (collected {})".format(
            info["total_subjects"], str(info.get("collected_at", "?"))[:10]))
    else:
        print("  No academic database found. Use Option 4 to collect GTU data.")

    _divider()
    return cache, internet_ok, gtu_ok


# ── Main menu ──────────────────────────────────────────────────────────────────

def print_main_menu() -> None:
    _header("MAIN MENU")
    print("  1. Download Previous Year Papers  (PYQ)")
    print("  2. Download Syllabus")
    print("  3. Download PYQs + Syllabus")
    print("  4. Refresh GTU Academic Data  [browser collector]")
    print("  5. Search Subjects")
    print("  6. Download History")
    print("  7. Cache Manager")
    print("  8. Settings")
    print("  9. About")
    print("  0. Exit")
    _divider()


# ── Subject selection helpers ──────────────────────────────────────────────────

def _pick_subject(cache: CacheManager) -> Optional[Dict]:
    """Get subject via hierarchical selector, or manual entry if no cache data."""

    if cache.has_academic_data():
        # --- Smart selector path ---
        from .selector.subject_selector import SubjectSelector
        selector = SubjectSelector(cache)
        subject = selector.run()
        return subject
    else:
        # --- Manual entry fallback (always works) ---
        print("  NOTE: No academic database found.")
        print("  Run Option 4 first to enable smart subject selection.")
        print("  For now, enter the subject code manually.\n")
        code = input("  Enter Subject Code (e.g. 3170719): ").strip()
        if not code:
            return None
        name = input("  Subject Name (optional, press Enter to skip): ").strip()
        # Return a minimal subject dict so the download flows work
        return {
            "subject_code": code,
            "subject_name": name or code,
            "course": "BE",
            "branch": "Unknown",
            "semester": "",
            "elective_type": "",
        }


def _subject_output_dir(subject: Dict, base_dir: Path) -> Path:
    """Return the structured download path for a subject."""
    from .downloader.syllabus_downloader import get_structured_output_dir
    return get_structured_output_dir(subject, base_dir)


def _record_history(hm: HistoryManager, entry_type: str, subject: Dict, extra: Dict) -> None:
    hm.append({
        "timestamp": _utc_now(),
        "type": entry_type,
        "subject_code": subject.get("subject_code"),
        "subject_name": subject.get("subject_name"),
        "course": subject.get("course"),
        "branch": subject.get("branch"),
        "semester": subject.get("semester"),
        **extra,
    })


# ── Option 1: Download PYQs ────────────────────────────────────────────────────

def download_pyq_flow(cache: CacheManager, settings: SettingsManager, internet_ok: bool) -> None:
    """Download Previous Year Papers using hierarchical subject selector."""
    _header("Download Previous Year Papers")

    if not internet_ok:
        print("  WARNING: No internet connection. Cannot download.")
        return

    print("  Select a subject to download PYQs for.\n")
    subject = _pick_subject(cache)
    if not subject:
        return

    subject_code = subject["subject_code"]
    out_dir = _subject_output_dir(subject, config.downloads_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from gtu_pyq_downloader.config import GTUPYQConfig
        from gtu_pyq_downloader.services.pipeline import GTUPYQPipeline
    except ImportError:
        print("  ERROR: PYQ downloader package not available. Run: pip install -e .")
        return

    try:
        v1_config = GTUPYQConfig()
        v1_config.downloads_dir = out_dir.parent

        pipeline = GTUPYQPipeline(v1_config, logger)
        print("\n  Starting download for [{}] {}".format(
            subject_code, subject.get("subject_name", "")))
        start = time.monotonic()

        result = pipeline.run(subject_code)

        elapsed = time.monotonic() - start
        print("\n  Download complete in {:.1f}s".format(elapsed))
        print("    Papers found  : {}".format(result.total_found))
        print("    Papers missing: {}".format(result.total_missing))
        print("    Output        : {}".format(result.output_path))

        _write_metadata_and_report(subject, result, out_dir / subject_code, elapsed)

        hm = HistoryManager()
        _record_history(hm, "PYQ", subject, {
            "papers_found": result.total_found,
            "papers_missing": result.total_missing,
            "output_path": str(result.output_path),
            "execution_time_sec": round(elapsed, 2),
        })

        pipeline.close()

    except Exception as exc:
        logger.exception("PYQ download failed")
        print("  ERROR: Download failed: {}".format(exc))


def _write_metadata_and_report(subject: Dict, pipeline_result, out_dir: Path, elapsed: float) -> None:
    """Write metadata.json and report.txt beside the merged PDF."""
    from .metadata.metadata_manager import MetadataManager
    from .reports.report_generator import generate_report

    # PaperResult uses .session attribute for the session code
    try:
        papers = getattr(pipeline_result, "papers", [])
        downloaded = []
        missing = []
        for p in papers:
            sess = getattr(p, "session", None) or str(p)
            if getattr(p, "is_available", False):
                downloaded.append(sess)
            else:
                missing.append(sess)
    except Exception:
        downloaded, missing = [], []

    meta = {
        "course": subject.get("course"),
        "branch": subject.get("branch_name", subject.get("branch")),
        "semester": subject.get("semester"),
        "academic_year": subject.get("academic_year"),
        "elective_type": subject.get("elective_type"),
        "subject_name": subject.get("subject_name"),
        "subject_code": subject.get("subject_code"),
        "downloaded": downloaded,
        "missing": missing,
        "execution_time": round(elapsed, 2),
        "created_at": _utc_now(),
    }
    try:
        mm = MetadataManager()
        mm.save_metadata(out_dir, meta)
        generate_report(out_dir, meta)
    except Exception as exc:
        logger.warning("Could not write metadata/report: %s", exc)


# ── Option 2: Download Syllabus ────────────────────────────────────────────────

def download_syllabus_flow(cache: CacheManager, settings: SettingsManager, internet_ok: bool) -> None:
    """Download Syllabus using hierarchical subject selector."""
    _header("Download Syllabus")

    if not internet_ok:
        print("  WARNING: No internet connection. Cannot download.")
        return

    print("  Select a subject to download its syllabus.\n")
    subject = _pick_subject(cache)
    if not subject:
        return

    from .downloader.syllabus_downloader import SyllabusDownloader
    dl = SyllabusDownloader(base_dir=config.downloads_dir)
    saved_path = dl.download(subject)

    if saved_path:
        hm = HistoryManager()
        _record_history(hm, "Syllabus", subject, {"output_path": str(saved_path)})


# ── Option 3: Combined PYQ + Syllabus ─────────────────────────────────────────

def combined_download_flow(cache: CacheManager, settings: SettingsManager, internet_ok: bool) -> None:
    """Download PYQs + Syllabus for a selected subject."""
    _header("Download PYQs + Syllabus")

    if not internet_ok:
        print("  WARNING: No internet connection. Cannot download.")
        return

    print("  Select a subject to download PYQs and syllabus for.\n")
    subject = _pick_subject(cache)
    if not subject:
        return

    subject_code = subject["subject_code"]

    # --- PYQs ---
    print("\n  [1/2] Downloading PYQs for [{}] {}...".format(
        subject_code, subject.get("subject_name", "")))
    try:
        from gtu_pyq_downloader.config import GTUPYQConfig
        from gtu_pyq_downloader.services.pipeline import GTUPYQPipeline

        v1_config = GTUPYQConfig()
        out_dir = _subject_output_dir(subject, config.downloads_dir)
        v1_config.downloads_dir = out_dir.parent

        pipeline = GTUPYQPipeline(v1_config, logger)
        start = time.monotonic()
        result = pipeline.run(subject_code)
        elapsed = time.monotonic() - start
        pipeline.close()

        print("  PYQs: {} found, {} missing  ({:.1f}s)".format(
            result.total_found, result.total_missing, elapsed))
        _write_metadata_and_report(subject, result, out_dir / subject_code, elapsed)

        hm = HistoryManager()
        _record_history(hm, "PYQ", subject, {
            "papers_found": result.total_found,
            "papers_missing": result.total_missing,
            "execution_time_sec": round(elapsed, 2),
        })
    except Exception as exc:
        logger.exception("PYQ download failed in combined flow")
        print("  ERROR: PYQ download failed: {}".format(exc))

    # --- Syllabus ---
    print("\n  [2/2] Downloading syllabus for [{}]...".format(subject_code))
    from .downloader.syllabus_downloader import SyllabusDownloader
    dl = SyllabusDownloader(base_dir=config.downloads_dir)
    saved = dl.download(subject)
    if saved:
        hm = HistoryManager()
        _record_history(hm, "Syllabus", subject, {"output_path": str(saved)})


# ── Option 4: Refresh GTU Academic Data ───────────────────────────────────────

def refresh_cache_flow(cache: CacheManager) -> None:
    """Run the browser-based academic collector to refresh cached data."""
    _header("Refresh GTU Academic Data")
    print("  This will launch a headless browser and collect all academic")
    print("  data from the GTU syllabus portal. This may take several minutes.\n")

    headed = input("  Run in visible browser mode for debugging? (y/N): ").strip().lower() == "y"

    print("\n  Starting GTU Academic Collector...")
    print("  Press Ctrl+C to abort.\n")

    try:
        from .collector.academic_collector import AcademicCollector
        collector = AcademicCollector(
            headless=not headed,
            cache_dir=cache.cache_dir,
        )
        result = collector.run()
        AcademicCollector.print_summary(result)

        # Offer exports
        print("\n  Export collected data?")
        print("  1. Export CSV + XLSX + report  2. Skip")
        choice = input("  Choice: ").strip()
        if choice == "1":
            from .collector.exporter import export_all
            export_dir = config.project_root / "exports"
            paths = export_all(result, export_dir)
            print("\n  Exported:")
            for fmt, p in paths.items():
                print("    {}: {}".format(fmt.upper(), p))

        # Update simple cache files too for backwards compat
        subjects = result.get("subjects", [])
        cache.save("last_refresh", _utc_now())
        courses = sorted({s.get("course") for s in subjects if s.get("course")})
        cache.save("courses", [{"id": c, "name": c} for c in courses])
        cache.save("subjects", subjects)

    except KeyboardInterrupt:
        print("\n\n  Collection aborted by user.")
    except RuntimeError as exc:
        print("\n  ERROR: {}".format(exc))
        print("  Install Playwright: pip install playwright && playwright install chromium")
    except Exception as exc:
        logger.exception("Academic data collection failed")
        print("\n  ERROR: Collection failed: {}".format(exc))


# ── Option 5: Search Subjects ──────────────────────────────────────────────────

def search_subjects_flow(cache: CacheManager) -> None:
    """Quick subject search by name or code."""
    _header("Search Subjects")

    if not cache.has_academic_data():
        print("  WARNING: No academic data. Run Option 4 first.")
        return

    query = input("  Search (name or code): ").strip()
    if not query:
        return

    results = cache.search_subjects(query, top_n=30)
    if not results:
        print("  No matches found.")
        return

    print("\n  Found {} result(s):\n".format(len(results)))
    for i, s in enumerate(results, 1):
        code = s.get("subject_code", "?")
        name = s.get("subject_name", "?")
        sem  = s.get("semester", "")
        elec = s.get("elective_type", "")
        course = s.get("course", "")
        branch = s.get("branch_name", s.get("branch", ""))
        print("  {:3d}. [{}] {}".format(i, code, name))
        print("       {} / {} / Sem {} / {}".format(course, branch, sem, elec))

    _divider()


# ── Option 6: Download History ─────────────────────────────────────────────────

def download_history_ui(cache: CacheManager) -> None:
    _header("Download History")
    hm = HistoryManager()
    entries = hm.list()

    if not entries:
        print("  No download history available.")
        return

    print("  Total downloads: {}\n".format(len(entries)))
    print("  Recent (last 20):")
    _divider()
    for i, e in enumerate(entries[-20:], 1):
        ts = e.get("timestamp", "?")[:19].replace("T", " ")
        etype = e.get("type", "?")
        code = e.get("subject_code", "?")
        name = e.get("subject_name", "")
        found = e.get("papers_found", "")
        found_str = ", found={}".format(found) if found != "" else ""
        print("  {:2d}. [{}] {} - {} {}{}".format(i, ts, etype, code, name, found_str))
    _divider()

    print("  1 Export CSV  2 Clear history  3 Back")
    choice = input("  Choice: ").strip()

    if choice == "1":
        dest = Path(input("  Export path (csv file): ").strip())
        try:
            hm.export_csv(dest)
            print("  Exported to {}".format(dest))
        except Exception as exc:
            print("  ERROR: Export failed: {}".format(exc))
    elif choice == "2":
        if input("  Clear all history? (y/N): ").strip().lower() == "y":
            hm.history_file.unlink(missing_ok=True)
            print("  History cleared.")


# ── Option 7: Cache Manager ────────────────────────────────────────────────────

def cache_manager_ui(cache: CacheManager) -> None:
    _header("Cache Manager")

    while True:
        stats = cache.stats()
        info = cache.get_academic_data_info()
        print("\n  Cache Status:")
        print("    Files     : {}".format(stats.get("files", 0)))
        print("    Size      : {:.1f} KB".format(stats.get("size_bytes", 0) / 1024))
        if info.get("exists"):
            print("    Subjects  : {}".format(info["total_subjects"]))
            print("    Collected : {}".format(str(info.get("collected_at", "?"))[:19]))
        counts = stats.get("counts", {})
        for name in ["courses", "branches"]:
            val = counts.get(name)
            if val is not None and val > 0:
                print("    {}: {}".format(name, val))

        print("\n  Options:")
        print("    1. View cache contents")
        print("    2. Export cache file")
        print("    3. Import cache file")
        print("    4. Delete cache file")
        print("    5. Delete ALL academic data  (force re-collect)")
        print("    6. Back")

        choice = input("  Choice: ").strip()

        if choice == "1":
            caches = cache.list_caches()
            for name in caches:
                data = cache.load(name)
                if isinstance(data, list):
                    print("    {}: {} items".format(name, len(data)))
                elif isinstance(data, dict):
                    print("    {}: {} keys".format(name, len(data)))
                else:
                    print("    {}: {}".format(name, type(data).__name__))
        elif choice == "2":
            name = input("  Cache name to export: ").strip()
            dest = Path(input("  Destination file: ").strip())
            try:
                cache.export(name, dest)
                print("  Exported {} -> {}".format(name, dest))
            except Exception as exc:
                print("  ERROR: Export failed: {}".format(exc))
        elif choice == "3":
            src = Path(input("  Source file path: ").strip())
            name = input("  Import as (cache name): ").strip()
            try:
                cache.import_cache(src, name)
                print("  Imported as {}".format(name))
            except Exception as exc:
                print("  ERROR: Import failed: {}".format(exc))
        elif choice == "4":
            name = input("  Cache name to delete: ").strip()
            if input("  Delete {}? (y/N): ".format(name)).strip().lower() == "y":
                cache.delete(name)
                print("  Deleted {}".format(name))
        elif choice == "5":
            if input("  Delete ALL academic data and re-collect? (y/N): ").strip().lower() == "y":
                cache.delete("gtu_academic_data")
                cache.delete("courses")
                cache.delete("branches")
                cache.delete("subjects")
                print("  Academic data cleared. Run Option 4 to re-collect.")
        elif choice == "6":
            break
        else:
            print("  Invalid option.")


# ── Option 8: Settings ─────────────────────────────────────────────────────────

def settings_ui(settings: SettingsManager) -> None:
    _header("Settings")

    while True:
        print("\n  Current Settings:")
        _divider()
        print("   1. Retry count       : {}".format(settings.get("retry_count")))
        print("   2. Timeout (sec)     : {}".format(settings.get("timeout_seconds")))
        print("   3. Auto merge        : {}".format(settings.get("auto_merge")))
        print("   4. Auto refresh cache: {}".format(settings.get("auto_refresh_cache")))
        print("   5. Merge order       : {}".format(settings.get("default_merge_order")))
        print("   6. Session order     : {}".format(settings.get("default_session_order")))
        print("   7. Progress bar      : {}".format(settings.get("progress_bar")))
        print("   8. Logging level     : {}".format(settings.get("logging_level")))
        print("   9. Reset to defaults")
        print("  10. Back")
        _divider()

        choice = input("  Choice: ").strip()

        if choice == "1":
            try:
                val = int(input("  Retry count (1-10): "))
                if 1 <= val <= 10:
                    settings.set("retry_count", val)
                    print("  Updated.")
            except ValueError:
                print("  Invalid input.")
        elif choice == "2":
            try:
                val = int(input("  Timeout seconds (5-60): "))
                if 5 <= val <= 60:
                    settings.set("timeout_seconds", val)
                    print("  Updated.")
            except ValueError:
                print("  Invalid input.")
        elif choice == "3":
            val = input("  Auto merge (y/n): ").strip().lower() == "y"
            settings.set("auto_merge", val)
            print("  Updated.")
        elif choice == "4":
            val = input("  Auto refresh cache (y/n): ").strip().lower() == "y"
            settings.set("auto_refresh_cache", val)
            print("  Updated.")
        elif choice == "5":
            order = input("  Merge order (ascending/descending): ").strip().lower()
            if order in ["ascending", "descending"]:
                settings.set("default_merge_order", order)
                print("  Updated.")
        elif choice == "6":
            order = input("  Session order (winter-first/summer-first): ").strip().lower()
            if order in ["winter-first", "summer-first"]:
                settings.set("default_session_order", order)
                print("  Updated.")
        elif choice == "7":
            val = input("  Progress bar (y/n): ").strip().lower() == "y"
            settings.set("progress_bar", val)
            print("  Updated.")
        elif choice == "8":
            level = input("  Logging level (DEBUG/INFO/WARNING/ERROR): ").strip().upper()
            if level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                settings.set("logging_level", level)
                print("  Updated.")
        elif choice == "9":
            if input("  Reset to defaults? (y/N): ").strip().lower() == "y":
                settings.reset()
                print("  Reset.")
        elif choice == "10":
            break
        else:
            print("  Invalid option.")


# ── Option 9: About ────────────────────────────────────────────────────────────

def about_screen() -> None:
    _header("About GTU Academic Engine V2")
    print("""
  Comprehensive academic resource management system for GTU students.

  - Smart subject selector (Course -> Branch -> Sem -> Subject)
  - Browser-based academic data collector (Playwright)
  - Previous Year Question Paper (PYQ) Downloader
  - Syllabus Downloader
  - PDF Merger with session ordering
  - Fuzzy subject search
  - Intelligent caching (gtu_academic_data.json)
  - Download History with CSV export
  - Export to CSV / XLSX / Report
  - Comprehensive Logging (5 rotating log files)
  - Configurable Settings

  Version  : 2.0.0
  Build    : 2026-06-14
  License  : MIT
  GitHub   : https://github.com/Nishit3116/GTU
    """)
    _divider()
    input("  Press Enter to continue...")


# ── Main loop ──────────────────────────────────────────────────────────────────

# ── Main loop ──────────────────────────────────────────────────────────────────

def run_cli(cache: CacheManager, settings: SettingsManager, internet_ok: bool) -> None:
    """Run in interactive command-line interface mode."""
    while True:
        try:
            print_main_menu()
            choice = input("  Select an option: ").strip()

            if choice == "1":
                download_pyq_flow(cache, settings, internet_ok)
            elif choice == "2":
                download_syllabus_flow(cache, settings, internet_ok)
            elif choice == "3":
                combined_download_flow(cache, settings, internet_ok)
            elif choice == "4":
                refresh_cache_flow(cache)
            elif choice == "5":
                search_subjects_flow(cache)
            elif choice == "6":
                download_history_ui(cache)
            elif choice == "7":
                cache_manager_ui(cache)
            elif choice == "8":
                settings_ui(settings)
            elif choice == "9":
                about_screen()
            elif choice == "0":
                print("\n  Goodbye!\n")
                logger.info("Application exited normally")
                sys.exit(0)
            else:
                print("  Invalid option. Please try again.")

        except KeyboardInterrupt:
            print("\n\n  Interrupted by user. Goodbye!\n")
            sys.exit(0)
        except Exception as exc:
            logger.exception("Unexpected error in main loop")
            print("  Error: {}".format(exc))


def run() -> None:
    """Main application loop."""
    setup_logging()

    # If --cli argument is passed, run in terminal CLI mode
    if "--cli" in sys.argv:
        cache, internet_ok, gtu_ok = startup_checks()
        settings = SettingsManager()
        logger.info("Application started in CLI mode")
        run_cli(cache, settings, internet_ok)
        return

    # Default: Run the local Web Application UI
    _header("GTU Academic Engine V2")
    print("  Starting Web Application Server...")
    print("  To run in CLI mode instead, execute: python -m gtu_academic_engine --cli\n")

    import threading
    import webbrowser
    from .server import run_web_server

    port = 5000

    # Start built-in server in background thread
    server_thread = threading.Thread(target=run_web_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait briefly for server to boot, then launch browser
    time.sleep(1.2)
    web_url = f"http://localhost:{port}"
    print(f"  Opening web interface at: {web_url}")
    print("  Press Ctrl+C in this terminal to terminate the server.")
    webbrowser.open(web_url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Server stopped by user. Goodbye!\n")
        logger.info("Web server stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    run()
