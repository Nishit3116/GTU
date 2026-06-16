"""Built-in HTTP server for GTU Academic Engine V2 Web App UI.

Serves the frontend static files and exposes JSON APIs for cascading dropdowns,
live dynamic subject scraping, and downloading PYQs and syllabi on-demand.
"""

import mimetypes
import os
import json
import logging
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List

from .cache.cache_manager import CacheManager
from .provider.aspx_provider import STATIC_COURSES
from .provider.subprocess_provider import PlaywrightSubprocessWorker
from .downloader.syllabus_downloader import SyllabusDownloader, get_structured_output_dir
from .config import config

logger = logging.getLogger(__name__)

# Web static files directory — all frontend assets live here
WEB_DIR = Path(__file__).parent / "web"

# Canonical aliases: URL path  ->  filename inside WEB_DIR
_STATIC_ALIASES: Dict[str, str] = {
    "/": "index.html",
    "/index.html": "index.html",
    "/index.css": "index.css",
    "/index.js": "index.js",
    "/favicon.ico": "favicon.ico",
}


# ── Playwright subprocess worker ─────────────────────────────────────────────────
#
# sync_playwright() cannot be called inside the parent web-server process
# because Render (Linux + Python 3.12) always has a running asyncio event
# loop at startup.  Neither threading.Thread nor ThreadPoolExecutor solves
# this because both share the parent's event-loop state.
#
# Solution: run ASPXProvider in a multiprocessing.Process('spawn').
# A spawned process starts a FRESH Python interpreter with no asyncio,
# no inherited event loop — sync_playwright() works unconditionally.
# Communication: multiprocessing.Queue with picklable dicts/lists.
# ─────────────────────────────────────────────────────────────────

# Singleton — created once at module import time.
# The child process is spawned immediately and waits for tasks.
_PW_PROC: PlaywrightSubprocessWorker = PlaywrightSubprocessWorker()



class GTUWebHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler serving static files and API requests."""

    cache_manager = CacheManager()

    # ------------------------------------------------------------------
    # Playwright helper
    # ------------------------------------------------------------------

    def _pw_call(self, method: str, *args, **kwargs):
        """Delegate an ASPXProvider method call to the Playwright subprocess.

        The subprocess runs in a fresh Python interpreter (spawn context)
        with no asyncio event loop, so sync_playwright() works on Render.
        """
        return _PW_PROC.call(method, *args, timeout=120, **kwargs)

    def log_message(self, format, *args):
        # Override to suppress default HTTP logging to stdout to keep terminal clean
        logger.debug(format % args)

    def _send_json(self, status: int, data: Any) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_static(self, file_path: Path, content_type: str = "", download_name: str = "") -> None:
        """Stream *file_path* to the client with the correct Content-Type.

        If *content_type* is omitted, it is inferred from the file extension
        using mimetypes.guess_type so every asset type is served correctly.
        """
        if not file_path.exists() or not file_path.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File not found")
            return

        # Resolve content-type
        if not content_type:
            guessed, _ = mimetypes.guess_type(str(file_path))
            content_type = guessed or "application/octet-stream"

        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # ── Health-check endpoint (Render / uptime monitors) ──────────────────
        if path == "/health":
            info = self.cache_manager.get_academic_data_info()
            self._send_json(200, {
                "status": "OK",
                "service": "GTU Academic Engine V2",
                "version": "2.0",
                "cache_loaded": info.get("exists", False),
                "subjects_cached": info.get("total_subjects", 0),
            })
            return

        # ── Generic static file server ─────────────────────────────────────────
        # 1. Check canonical aliases (/, /index.html, /index.css, ...)
        if path in _STATIC_ALIASES:
            self._send_static(WEB_DIR / _STATIC_ALIASES[path])
            return

        # 2. Check for any file that physically exists inside WEB_DIR.
        #    Strip the leading '/' and resolve against WEB_DIR.
        #    Security: ensure the resolved path is still inside WEB_DIR.
        rel = urllib.parse.unquote(path.lstrip("/"))
        candidate = (WEB_DIR / rel).resolve()
        try:
            candidate.relative_to(WEB_DIR.resolve())   # raises ValueError if outside
        except ValueError:
            pass  # path traversal attempt — fall through to API router
        else:
            if candidate.is_file():
                self._send_static(candidate)
                return

        # 3. Downloads (PDFs served from the project downloads dir)
        if path.startswith("/downloads/"):
            rel_path = urllib.parse.unquote(path[1:])
            file_path = config.project_root / rel_path
            self._send_static(file_path, download_name=file_path.name)
            return

        # ── API routes ────────────────────────────────────────────────────────
        params = urllib.parse.parse_qs(parsed.query)
        # Flatten query parameters
        params = {k: v[0] for k, v in params.items() if v}

        try:
            if path == "/api/courses":
                # Static courses
                self._send_json(200, STATIC_COURSES)
                return

            elif path == "/api/branches":
                course_id = params.get("course")
                if not course_id:
                    self._send_json(400, {"error": "Missing course parameter"})
                    return
                # Check cache first
                branches = self._get_cached_branches(course_id)
                if branches:
                    self._send_json(200, branches)
                    return
                # On-demand live scrape
                logger.info("Scraping branches for course: %s", course_id)
                scraped = self._pw_call("fetch_branches", course_id)
                if scraped:
                    self._save_scraped_branches(course_id, scraped)
                self._send_json(200, scraped)
                return

            elif path == "/api/semesters":
                course_id = params.get("course")
                branch_id = params.get("branch")
                if not course_id or not branch_id:
                    self._send_json(400, {"error": "Missing parameters"})
                    return
                # Check cache first
                semesters = self._get_cached_semesters(course_id, branch_id)
                if semesters:
                    self._send_json(200, semesters)
                    return
                # Live scrape
                logger.info("Scraping semesters for %s/%s", course_id, branch_id)
                scraped = self._pw_call("fetch_semesters", course_id, branch_id)
                if scraped:
                    self._save_scraped_semesters(course_id, branch_id, scraped)
                self._send_json(200, scraped)
                return

            elif path == "/api/years":
                course_id = params.get("course")
                branch_id = params.get("branch")
                if not course_id or not branch_id:
                    self._send_json(400, {"error": "Missing parameters"})
                    return
                # Fetch live if possible to ensure we match GTU exactly
                try:
                    logger.info("Live fetching academic years from GTU for %s/%s", course_id, branch_id)
                    scraped = self._pw_call("fetch_academic_years", course_id, branch_id)
                    if scraped:
                        self._send_json(200, scraped)
                        return
                except Exception as exc:
                    logger.warning("Failed to fetch academic years live, falling back to cache: %s", exc)

                # Fallback to cache
                years = self._get_cached_years(course_id, branch_id)
                if years:
                    self._send_json(200, years)
                    return
                # Hardcoded fallback of last resort
                self._send_json(200, ["2018-19", "2024-25"])
                return

            elif path == "/api/electives":
                course_id = params.get("course")
                branch_id = params.get("branch")
                sem = params.get("sem")
                if not all([course_id, branch_id, sem]):
                    self._send_json(400, {"error": "Missing parameters"})
                    return
                # Check cache first
                electives = self._get_cached_electives(course_id, branch_id, sem)
                if electives:
                    self._send_json(200, electives)
                    return
                # Live scrape
                logger.info("Scraping electives for %s/%s sem=%s", course_id, branch_id, sem)
                scraped = self._pw_call("fetch_elective_types", course_id, branch_id, sem)
                self._send_json(200, scraped)
                return

            elif path == "/api/subjects":
                course = params.get("course")
                branch = params.get("branch")
                sem = params.get("sem")
                year = params.get("year", "")
                elective = params.get("elective", "")
                live_scrape = params.get("live", "true").lower() == "true"

                if not all([course, branch, sem]):
                    self._send_json(400, {"error": "Missing parameters"})
                    return

                # Check cache first
                elective_filter = None if elective in ("", "All") else elective
                cached_subjects = self.cache_manager.get_subjects(
                    course=course, branch=branch, year=year or None, semester=sem, elective_type=elective_filter
                )
                if cached_subjects or not live_scrape:
                    self._send_json(200, cached_subjects)
                    return

                # Live scrape on-demand
                if elective_filter:
                    logger.info("Scraping subjects for %s/%s/sem=%s/year=%s/elec=%s", course, branch, sem, year, elective_filter)
                    scraped = self._pw_call("fetch_subjects", course, branch, sem, elective_filter, academic_year=year)
                else:
                    logger.info("Scraping subjects for %s/%s/sem=%s/year=%s/elec=All", course, branch, sem, year)
                    scraped = self._pw_call("fetch_subjects_both_electives", course, branch, sem, academic_year=year)

                # Fetch full names for metadata enrichment if we have cache
                c_name = course
                b_name = branch
                for c in STATIC_COURSES:
                    if c["id"] == course:
                        c_name = c["name"]
                        break
                cached_b = self._get_cached_branches(course)
                for b in cached_b or []:
                    if b["id"] == branch:
                        b_name = b["name"]
                        break

                # Enrich
                for s in scraped:
                    s["course_name"] = c_name
                    s["branch_name"] = b_name
                    s["semester_label"] = f"Semester {sem}"

                # Cache dynamically fetched subjects to our local subjects cache
                # Merge into existing academic data if available
                db = self.cache_manager.load_academic_data() or {
                    "database": {},
                    "subjects": [],
                    "stats": {"success": True, "total_subjects": 0},
                    "collected_at": "",
                }
                for s in scraped:
                    if not any(
                        x.get("subject_code") == s["subject_code"]
                        and x.get("academic_year") == s["academic_year"]
                        for x in db["subjects"]
                    ):
                        db["subjects"].append(s)
                db["stats"]["total_subjects"] = len(db["subjects"])
                self.cache_manager.save_academic_data(db)

                self._send_json(200, scraped)
                return

            elif path == "/api/search":
                q = params.get("q", "")
                if not q:
                    self._send_json(200, [])
                    return
                results = self.cache_manager.search_subjects(q, top_n=50)
                
                # If no cached results, check live GTU portal
                import re
                if not results:
                    # Case A: Try to find a subject code (5 to 10 digits) in the query
                    code_match = re.search(r"\b\d{5,10}\b", q)
                    if code_match:
                        subject_code = code_match.group(0)
                        logger.info("Subject code %s extracted from query. Fetching live...", subject_code)
                        try:
                            scraped = self._pw_call("fetch_subject_by_code", subject_code)
                            if scraped:
                                # Save/cache the scraped subject details
                                db = self.cache_manager.load_academic_data() or {
                                    "database": {},
                                    "subjects": [],
                                    "stats": {"success": True, "total_subjects": 0},
                                    "collected_at": "",
                                }
                                for s in scraped:
                                    s["course_name"] = s.get("course", "BE")
                                    for c in STATIC_COURSES:
                                        if c["id"] == s["course"]:
                                            s["course_name"] = c["name"]
                                            break
                                    s["branch_name"] = s.get("branch", "")
                                    s["semester_label"] = f"Semester {s.get('semester', '')}"
                                    
                                    if not any(
                                        x.get("subject_code") == s["subject_code"]
                                        and x.get("academic_year") == s["academic_year"]
                                        for x in db["subjects"]
                                    ):
                                        db["subjects"].append(s)
                                db["stats"]["total_subjects"] = len(db["subjects"])
                                self.cache_manager.save_academic_data(db)
                                results = scraped
                        except Exception as exc:
                            logger.error("Failed live subject code search for %s: %s", subject_code, exc)
                    
                    # Case B: If no code is present, try live name search
                    else:
                        # Clean search query (strip quotes, standard prefixes)
                        name_query = q.replace("Ask AI Copilot...", "").replace("Search subjects...", "").strip()
                        name_query = re.sub(r"^['\"]|['\"]$", "", name_query).strip()
                        if len(name_query) >= 3:
                            logger.info("Subject name query '%s' received. Fetching live...", name_query)
                            try:
                                scraped = self._pw_call("fetch_subject_by_name", name_query)
                                if scraped:
                                    # Save/cache the scraped subject details
                                    db = self.cache_manager.load_academic_data() or {
                                        "database": {},
                                        "subjects": [],
                                        "stats": {"success": True, "total_subjects": 0},
                                        "collected_at": "",
                                    }
                                    for s in scraped:
                                        s["course_name"] = s.get("course", "BE")
                                        for c in STATIC_COURSES:
                                            if c["id"] == s["course"]:
                                                s["course_name"] = c["name"]
                                                break
                                        s["branch_name"] = s.get("branch", "")
                                        s["semester_label"] = f"Semester {s.get('semester', '')}"
                                        
                                        if not any(
                                            x.get("subject_code") == s["subject_code"]
                                            and x.get("academic_year") == s["academic_year"]
                                            for x in db["subjects"]
                                        ):
                                            db["subjects"].append(s)
                                    db["stats"]["total_subjects"] = len(db["subjects"])
                                    self.cache_manager.save_academic_data(db)
                                    results = scraped
                            except Exception as exc:
                                logger.error("Failed live subject name search for %s: %s", name_query, exc)
                
                self._send_json(200, results)
                return

            elif path == "/api/settings":
                from .utils.settings import SettingsManager
                settings = SettingsManager()
                self._send_json(200, settings.settings)
                return

            elif path == "/api/stats":
                info = self.cache_manager.get_academic_data_info()
                self._send_json(200, info)
                return

            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"API Route not found")

        except Exception as e:
            logger.exception("Web server error on API route %s", path)
            self._send_json(500, {"error": str(e)})

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/settings":
            try:
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode("utf-8"))

                from .utils.settings import SettingsManager
                settings = SettingsManager()
                for key, val in data.items():
                    if key in ("retry_count", "timeout_seconds", "parallel_downloads"):
                        settings.set(key, int(val))
                    elif key in ("auto_merge", "auto_refresh_cache", "progress_bar"):
                        settings.set(key, bool(val))
                    elif key in ("default_merge_order", "default_session_order", "logging_level"):
                        settings.set(key, str(val))
                self._send_json(200, {"status": "success", "settings": settings.settings})
                return
            except Exception as e:
                logger.exception("Save settings failed")
                self._send_json(500, {"error": str(e)})
                return

        elif parsed.path == "/api/download":
            try:
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode("utf-8"))

                subject = data.get("subject")
                dl_type = data.get("type", "both")  # pyq, syllabus, both

                if not subject or not subject.get("subject_code"):
                    self._send_json(400, {"error": "Missing subject data"})
                    return

                code = subject["subject_code"]
                name = subject.get("subject_name", code)
                out_dir = get_structured_output_dir(subject, config.downloads_dir)
                out_dir.mkdir(parents=True, exist_ok=True)

                results = {"pyq_success": False, "syllabus_success": False, "out_dir": str(out_dir)}

                # ── Download PYQs ─────────────────────────────────────────────
                if dl_type in ("pyq", "both"):
                    try:
                        from gtu_pyq_downloader.config import GTUPYQConfig
                        from gtu_pyq_downloader.services.pipeline import GTUPYQPipeline
                        from .utils.settings import SettingsManager

                        settings = SettingsManager()

                        overrides = data.get("settings", {})

                        v1_config = GTUPYQConfig()
                        v1_config.downloads_dir = out_dir.parent
                        v1_config.max_retries = int(overrides.get("retry_count", settings.get("retry_count", 3)))
                        v1_config.request_timeout = float(overrides.get("timeout_seconds", settings.get("timeout_seconds", 15)))

                        # Generate session list dynamically based on settings and overrides
                        from .downloader.session_generator import generate_sessions
                        session_order = overrides.get("session_order", settings.get("default_session_order", "winter-first"))
                        
                        start_year = int(overrides.get("start_year", 2018))
                        end_year = int(overrides.get("end_year", 2026))
                        
                        sessions = generate_sessions(start_year, end_year, order=session_order)

                        merge_order = overrides.get("merge_order", settings.get("default_merge_order", "ascending"))
                        if merge_order == "ascending":
                            v1_config.sessions = list(reversed(sessions))
                        else:
                            v1_config.sessions = sessions

                        pipeline = GTUPYQPipeline(v1_config, logger)

                        pipeline_result = pipeline.run(code)
                        results["pyq_success"] = True
                        results["pyq_found"] = pipeline_result.total_found
                        results["pyq_missing"] = pipeline_result.total_missing

                        # Get relative path for browser download
                        output_path = pipeline_result.output_path
                        if output_path:
                            try:
                                rel_pyq = Path(output_path).relative_to(config.project_root)
                                results["pyq_url"] = "/" + rel_pyq.as_posix()
                            except ValueError:
                                results["pyq_url"] = None

                        # Write metadata and report
                        from .main import _write_metadata_and_report
                        _write_metadata_and_report(subject, pipeline_result, out_dir / code, 5.0)
                        pipeline.close()
                    except Exception as exc:
                        logger.exception("PYQ download failed in web API")
                        results["pyq_error"] = str(exc)

                # ── Download Syllabus ─────────────────────────────────────────
                if dl_type in ("syllabus", "both"):
                    try:
                        # Route syllabus download through the Playwright executor so
                        # download_syllabus() runs on the dedicated worker thread.
                        subject_code = subject["subject_code"]

                        pdf_bytes = _PW_PROC.call("download_syllabus", subject_code, timeout=60)

                        if pdf_bytes:
                            # SyllabusDownloader handles path construction + saving
                            dl = SyllabusDownloader(base_dir=config.downloads_dir)
                            # Write bytes directly — no need to re-open ASPXProvider
                            from .downloader.syllabus_downloader import _structured_output_dir, _validate_pdf_bytes
                            if _validate_pdf_bytes(pdf_bytes):
                                out_path = _structured_output_dir(subject, config.downloads_dir) / "syllabus.pdf"
                                out_path.parent.mkdir(parents=True, exist_ok=True)
                                out_path.write_bytes(pdf_bytes)
                                results["syllabus_success"] = True
                                results["syllabus_path"] = str(out_path)
                                try:
                                    rel_syllabus = out_path.relative_to(config.project_root)
                                    results["syllabus_url"] = "/" + rel_syllabus.as_posix()
                                except ValueError:
                                    results["syllabus_url"] = None
                        else:
                            # Fallback: try direct HTTP download (no Playwright)
                            dl = SyllabusDownloader(base_dir=config.downloads_dir)
                            saved_path = dl._download_direct(subject["subject_code"])
                            if saved_path:
                                results["syllabus_success"] = True
                    except Exception as exc:
                        logger.exception("Syllabus download failed in web API")
                        results["syllabus_error"] = str(exc)

                self._send_json(200, {"status": "success", "results": results})

            except Exception as e:
                logger.exception("Download POST failed")
                self._send_json(500, {"error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _get_cached_branches(self, course_id: str) -> List[Dict]:
        db = self.cache_manager.load_academic_data()
        if not db or "database" not in db:
            return []
        course_data = db["database"].get(course_id, {})
        branches_data = course_data.get("_branches", {})
        result = []
        for bid, val in branches_data.items():
            meta = val.get("_meta", {})
            result.append({"id": bid, "name": meta.get("name", bid), "course_id": course_id})
        return sorted(result, key=lambda x: x["id"])

    def _get_cached_semesters(self, course_id: str, branch_id: str) -> List[Dict]:
        db = self.cache_manager.load_academic_data()
        if not db or "database" not in db:
            return []
        course_data = db["database"].get(course_id, {})
        branch_data = course_data.get("_branches", {}).get(branch_id, {})
        semesters_data = branch_data.get("_semesters", {})
        result = []
        for sem_val, val in semesters_data.items():
            meta = val.get("_meta", {})
            result.append({"value": sem_val, "text": meta.get("text", f"Semester {sem_val}")})
        return sorted(result, key=lambda x: x["value"])

    def _get_cached_years(self, course_id: str, branch_id: str) -> List[str]:
        # Return academic years present in cached subjects for this branch
        subjects = self.cache_manager.get_subjects(course=course_id, branch=branch_id)
        years = sorted({s["academic_year"] for s in subjects if s.get("academic_year")})
        return list(years)

    def _get_cached_electives(self, course_id: str, branch_id: str, sem: str) -> List[str]:
        db = self.cache_manager.load_academic_data()
        if not db or "database" not in db:
            return []
        course_data = db["database"].get(course_id, {})
        branch_data = course_data.get("_branches", {}).get(branch_id, {})
        sem_data = branch_data.get("_semesters", {}).get(sem, {})
        electives = list(sem_data.get("_electives", {}).keys())
        return electives if electives else ["Non_Elective", "Elective"]

    def _save_scraped_branches(self, course_id: str, scraped: List[Dict]) -> None:
        db = self.cache_manager.load_academic_data() or {
            "database": {},
            "subjects": [],
            "stats": {"success": True, "total_subjects": 0},
            "collected_at": "",
        }
        if "database" not in db:
            db["database"] = {}

        course_name = course_id
        for c in STATIC_COURSES:
            if c["id"] == course_id:
                course_name = c["name"]
                break

        if course_id not in db["database"]:
            db["database"][course_id] = {
                "_meta": {
                    "id": course_id,
                    "name": course_name
                },
                "_branches": {}
            }

        branches_data = db["database"][course_id].setdefault("_branches", {})
        for b in scraped:
            bid = b["id"]
            if bid not in branches_data:
                branches_data[bid] = {
                    "_meta": {
                        "name": b["name"]
                    },
                    "_semesters": {}
                }
        self.cache_manager.save_academic_data(db)

    def _save_scraped_semesters(self, course_id: str, branch_id: str, scraped: List[Dict]) -> None:
        db = self.cache_manager.load_academic_data() or {
            "database": {},
            "subjects": [],
            "stats": {"success": True, "total_subjects": 0},
            "collected_at": "",
        }
        if "database" not in db:
            db["database"] = {}

        course_name = course_id
        for c in STATIC_COURSES:
            if c["id"] == course_id:
                course_name = c["name"]
                break

        if course_id not in db["database"]:
            db["database"][course_id] = {
                "_meta": {
                    "id": course_id,
                    "name": course_name
                },
                "_branches": {}
            }

        branches_data = db["database"][course_id].setdefault("_branches", {})
        if branch_id not in branches_data:
            branches_data[branch_id] = {
                "_meta": {
                    "name": branch_id
                },
                "_semesters": {}
            }

        semesters_data = branches_data[branch_id].setdefault("_semesters", {})
        for s in scraped:
            val = str(s["value"])
            if val not in semesters_data:
                semesters_data[val] = {
                    "_meta": {
                        "text": s["text"]
                    },
                    "_electives": {}
                }
        self.cache_manager.save_academic_data(db)


def run_web_server(port: int = 5000) -> None:
    """Start the HTTP server and block until a KeyboardInterrupt or SIGTERM.

    Binds to 0.0.0.0 (empty string) so it is reachable on all network
    interfaces — required for cloud platforms such as Render.
    """
    # ── Startup banner ────────────────────────────────────────────────────────
    sep = "================================================"

    # Step 1: Cache
    try:
        _cm = CacheManager()
        info = _cm.get_academic_data_info()
        if info.get("exists"):
            cache_line = f"  Loading Cache...         ({info['total_subjects']} subjects)"
        else:
            cache_line = "  Loading Cache...         (empty — will scrape live)"
    except Exception as exc:
        cache_line = f"  Loading Cache...         WARNING: {exc}"
        logger.warning("Cache check failed at startup: %s", exc)

    # Step 2: Playwright
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        pw_line = "  Initializing Playwright... OK"
    except ImportError:
        pw_line = "  Initializing Playwright... NOT INSTALLED (run: playwright install chromium)"
        logger.warning("Playwright is not installed — live scraping will be unavailable.")
    except Exception as exc:
        pw_line = f"  Initializing Playwright... WARNING: {exc}"
        logger.warning("Playwright check failed: %s", exc)

    # Step 3: Directories
    try:
        from .config import config as _cfg
        _cfg.ensure_dirs()
        dir_line = "  Checking Directories...  OK"
    except Exception as exc:
        dir_line = f"  Checking Directories...  WARNING: {exc}"
        logger.warning("Directory creation failed: %s", exc)

    banner = (
        f"\n{sep}\n"
        f"\n  GTU Academic Engine V2.0\n"
        f"\n{cache_line}\n"
        f"\n{pw_line}\n"
        f"\n{dir_line}\n"
        f"\n  Server Ready\n"
        f"\n  Listening on PORT {port}\n"
        f"\n{sep}\n"
    )
    print(banner)
    for line in [
        sep, "GTU Academic Engine V2.0", cache_line.strip(),
        pw_line.strip(), dir_line.strip(),
        "Server Ready", f"Listening on PORT {port}", sep,
    ]:
        logger.info(line)

    # ── Bind and serve ────────────────────────────────────────────────────────
    # Empty string → 0.0.0.0 (all interfaces). Do NOT use "localhost" or
    # "127.0.0.1" — that would make the service unreachable on Render.
    server_address = ("", port)
    httpd = HTTPServer(server_address, GTUWebHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down server...")
        logger.info("KeyboardInterrupt received — stopping web server.")
    finally:
        # ── Graceful shutdown ──────────────────────────────────────────────────
        httpd.server_close()
        logger.info("HTTP server closed.")

        # Stop the Playwright subprocess
        logger.info("Stopping Playwright subprocess worker...")
        _PW_PROC.stop()


        logger.info("GTU Academic Engine V2 shut down cleanly.")
