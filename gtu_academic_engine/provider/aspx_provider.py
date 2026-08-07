"""GTU ASPX Provider - Playwright-based concrete GTUDataProvider.

Drives the GTU syllabus portal (https://gtu.ac.in/syllabus/syllabus.aspx)
using Playwright's synchronous API.

The portal uses ASP.NET WebForms with cascading dropdowns.
Actual HTML element IDs (verified from live page 2026-06-14):
  Course   : ContentPlaceHolder1_ddcourse
  Branch   : ContentPlaceHolder1_ddlbrcode   (loaded after course selection)
  Semester : ContentPlaceHolder1_ddsem        (loaded after branch selection)
  Acad Year: ContentPlaceHolder1_ddl_effFrom  (loaded after branch selection)
  Elective : ContentPlaceHolder1_ddl_iselective (loaded after semester)
  Sub Code : ContentPlaceHolder1_txtsubcode   (text input)
  Sub Name : ContentPlaceHolder1_txtsubjectname (text input)
  Search   : ContentPlaceHolder1_btn_search   (submit button)

Results appear in a table inside #ContentPlaceHolder1_pnl after Search is clicked.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .gtu_data_provider import GTUDataProvider
from ..constants import (
    SYLLABUS_PORTAL_URL,
    ASPX_COURSE_SELECT,
    ASPX_BRANCH_SELECT,
    ASPX_SEMESTER_SELECT,
    ASPX_YEAR_SELECT,
    ASPX_ELECTIVE_SELECT,
    ASPX_SUBJECT_CODE_INPUT,
    ASPX_SUBJECT_NAME_INPUT,
    ASPX_SEARCH_BUTTON,
    ASPX_RESULTS_PANEL,
    SYLLABUS_S3_FALLBACK_URL,
)

logger = logging.getLogger(__name__)

# ── Exact element IDs from live HTML ──────────────────────────────────────────
# (now imported from constants.py for centralized management)
ID_COURSE   = ASPX_COURSE_SELECT
ID_BRANCH   = ASPX_BRANCH_SELECT
ID_SEM      = ASPX_SEMESTER_SELECT
ID_YEAR     = ASPX_YEAR_SELECT
ID_ELECTIVE = ASPX_ELECTIVE_SELECT
ID_SUBCODE  = ASPX_SUBJECT_CODE_INPUT
ID_SUBNAME  = ASPX_SUBJECT_NAME_INPUT
ID_SEARCH   = ASPX_SEARCH_BUTTON
ID_RESULT   = ASPX_RESULTS_PANEL

# Legacy reference (use SYLLABUS_PORTAL_URL from constants)
SYLLABUS_URL = SYLLABUS_PORTAL_URL

# ── All courses from the static HTML (no AJAX needed) ─────────────────────────
STATIC_COURSES = [
    {"id": "IB", "name": "Applied Science- IB"},
    {"id": "CS", "name": "Applied Science-CS"},
    {"id": "DB", "name": "Applied Science-DB"},
    {"id": "IM", "name": "Applied Science-IM"},
    {"id": "EP", "name": "Bachelor of Engineering (Part Time)"},
    {"id": "BI", "name": "BACHELOR OF INTERIOR DESIGN"},
    {"id": "BL", "name": "Bachelor of Planning"},
    {"id": "BS", "name": "BACHELOR OF SCIENCE"},
    {"id": "BA", "name": "BARCH"},
    {"id": "BB", "name": "BBA"},
    {"id": "BC", "name": "BCA"},
    {"id": "BN", "name": "Bdesign"},
    {"id": "BE", "name": "BE"},
    {"id": "BH", "name": "BHMCT"},
    {"id": "BP", "name": "BPHARM"},
    {"id": "PP", "name": "BPP"},
    {"id": "BV", "name": "BVoc"},
    {"id": "DI", "name": "DIPLOMA"},
    {"id": "DA", "name": "Diploma arc"},
    {"id": "DP", "name": "DPHARM"},
    {"id": "DV", "name": "DVoc"},
    {"id": "MA", "name": "IMBA"},
    {"id": "MR", "name": "M. Arch."},
    {"id": "MH", "name": "MAHS"},
    {"id": "MN", "name": "Master of Planning"},
    {"id": "MB", "name": "MBA"},
    {"id": "MV", "name": "MBA (part time)"},
    {"id": "MC", "name": "MCA"},
    {"id": "IC", "name": "MCA Integrated"},
    {"id": "ME", "name": "ME"},
    {"id": "MP", "name": "MPHARM"},
    {"id": "ML", "name": "MPHIL"},
    {"id": "PD", "name": "PDDC"},
    {"id": "PI", "name": "PGD"},
    {"id": "DM", "name": "PGDDM"},
    {"id": "DS", "name": "PGDDS"},
    {"id": "DH", "name": "PGDHM"},
    {"id": "PR", "name": "PGDIPR"},
    {"id": "FD", "name": "PharmD"},
    {"id": "PB", "name": "PharmD(PB)"},
    {"id": "PH", "name": "PHD"},
]

_SETTLE_MS = 2000   # ms to wait for AJAX/postback to settle after selection
_TIMEOUT_MS = 20000


def _get_select_options(page: Any, css_id: str, skip_placeholder: bool = True) -> List[Dict[str, str]]:
    """Read all <option> values from a <select> element by CSS id."""
    try:
        opts = page.eval_on_selector(
            css_id,
            "sel => Array.from(sel.options).map(o => ({value: o.value, text: o.text.trim()}))",
        )
    except Exception as exc:
        logger.debug("Could not read options for %s: %s", css_id, exc)
        return []

    result = []
    for o in opts:
        val = (o.get("value") or "").strip()
        text = (o.get("text") or "").strip()
        if not val or not text:
            continue
        # Skip placeholder / default options
        if skip_placeholder and (
            val in ("Select course", "Select Branch", "Semester", "Sem",
                    "Academic Year", "Elective / Non-Elective",
                    "Elective", "0", "-1")
            or text.lower().startswith("select ")
        ):
            continue
        result.append({"value": val, "text": text})
    return result


def _select_and_wait(page: Any, css_id: str, value: str, next_css_id: str = None, settle_ms: int = 800) -> bool:
    """Select a dropdown value and dynamically wait for the next select element to populate."""
    try:
        # Check if already selected and next dropdown is ready
        try:
            curr_val = page.eval_on_selector(css_id, "sel => sel.value")
            if curr_val == value:
                if next_css_id:
                    next_ok = page.eval_on_selector(next_css_id, "sel => !sel.disabled && sel.options.length > 1")
                    if next_ok:
                        logger.debug("Dropdown %s already set to %s and next %s is ready. Skipping.", css_id, value, next_css_id)
                        return True
                else:
                    logger.debug("Dropdown %s already set to %s. Skipping.", css_id, value)
                    return True
        except Exception:
            pass

        old_count = 0
        if next_css_id:
            try:
                old_count = page.eval_on_selector(next_css_id, "sel => sel.options.length")
            except Exception:
                pass

        page.select_option(css_id, value=value, timeout=4000)
        
        # Wait a tiny bit for postback to start if any
        page.wait_for_timeout(250)
        
        if next_css_id:
            try:
                page.wait_for_function(
                    """([sel, old]) => {
                        if (typeof Sys !== 'undefined' && Sys.WebForms && Sys.WebForms.PageRequestManager) {
                            if (Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostback()) {
                                return false;
                            }
                        }
                        return !sel.disabled && sel.options.length > 1 && sel.options.length !== old;
                    }""",
                    arg=[page.locator(next_css_id).element_handle(), old_count],
                    timeout=6000
                )
            except Exception as wait_exc:
                logger.debug("Dynamic wait timeout for %s, falling back to timeout: %s", next_css_id, wait_exc)
                page.wait_for_timeout(settle_ms)
        else:
            try:
                page.wait_for_function(
                    """() => {
                        if (typeof Sys !== 'undefined' && Sys.WebForms && Sys.WebForms.PageRequestManager) {
                            return !Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostback();
                        }
                        return true;
                    }""",
                    timeout=3000
                )
            except Exception:
                page.wait_for_timeout(settle_ms)
        return True
    except Exception as exc:
        logger.debug("select_option failed for %s=%s: %s", css_id, value, exc)
        return False



def _extract_subjects_from_table(page: Any, course: str, branch: str,
                                  semester: str, elective: str, year: str = "") -> List[Dict]:
    """Parse the GTU GridView result table and extract subject rows.

    Table structure (verified from live page 2026-06-14):
    Data rows have many cells and a PDF link in links[0].
    Relevant columns in data rows:
      cells[10] = Subject Code  (e.g. BE01000011 or 3170719)
      cells[11] = Branch Code
      cells[12] = Academic Year (e.g. 2024-25)
      cells[13] = Subject Name
    Detail sub-rows (expanded metadata) have no PDF links - skip them.
    """
    subjects = []
    seen_codes = set()
    try:
        rows = page.eval_on_selector_all(
            "#ContentPlaceHolder1_pnl tr",
            """rows => rows.map(r => ({
                cells: Array.from(r.querySelectorAll('td')).map(c => c.innerText.trim()),
                links: Array.from(r.querySelectorAll('a[href]')).map(a => a.href)
            }))"""
        )
        for row in rows:
            cells = row.get("cells", [])
            links = row.get("links", [])

            # Data rows have a PDF link
            pdf_links = [l for l in links if l and ".pdf" in l.lower()]
            if not pdf_links or len(cells) < 14:
                continue

            code = cells[10].strip() if len(cells) > 10 else ""
            row_year = cells[12].strip() if len(cells) > 12 else year
            name = cells[13].strip() if len(cells) > 13 else code

            if not code or code in seen_codes:
                continue
            seen_codes.add(code)

            subj = {
                "subject_code": code,
                "subject_name": name,
                "elective_type": elective,
                "course": course,
                "branch": branch,
                "semester": semester,
                "academic_year": row_year or year,
                "syllabus_pdf_url": pdf_links[0],
                
                # Teaching Scheme Hours
                "lectures": cells[16].strip() if len(cells) > 16 else "0",
                "tutorial": cells[17].strip() if len(cells) > 17 else "0",
                "practical": cells[18].strip() if len(cells) > 18 else "0",
                "pbl": cells[19].strip() if len(cells) > 19 else "NA",
                "credits": cells[20].strip() if len(cells) > 20 else "0",
                
                # Examination Marks
                "exam_e": cells[21].strip() if len(cells) > 21 else "0",
                "exam_m": cells[22].strip() if len(cells) > 22 else "0",
                "exam_i": cells[23].strip() if len(cells) > 23 else "0",
                "exam_v": cells[24].strip() if len(cells) > 24 else "0",
                "exam_total": cells[25].strip() if len(cells) > 25 else "0",
                
                # Nested Details Sub-row
                "detail_category": cells[1].replace("Category :", "").strip() if len(cells) > 1 else "",
                "detail_elective": cells[2].replace("Elective Subject:", "").strip() if len(cells) > 2 else "No",
                "detail_is_theory": cells[3].replace("IsTheory :", "").strip() if len(cells) > 3 else "No",
                "detail_theory_duration": cells[4].replace("Theory Exam Duration :", "").strip() if len(cells) > 4 else "0",
                "detail_is_practical": cells[5].replace("IsPractical :", "").strip() if len(cells) > 5 else "No",
                "detail_practical_duration": cells[6].replace("Practical Exam Duration :", "").strip() if len(cells) > 6 else "0",
                "detail_remark": cells[7].replace("Remark :", "").strip() if len(cells) > 7 else "N/A",
                "detail_is_functional": cells[8].replace("Isfunctional :", "").strip() if len(cells) > 8 else "No",
                "detail_is_semipractical": cells[9].replace("IsSemipractical :", "").strip() if len(cells) > 9 else "No",
            }
            subjects.append(subj)

    except Exception as exc:
        logger.debug("Table extraction failed: %s", exc)

    return subjects


def _extract_pdf_links(page: Any) -> List[str]:
    """Extract all PDF hrefs from the result panel."""
    try:
        links = page.eval_on_selector_all(
            "#ContentPlaceHolder1_pnl a[href]",
            "els => els.map(e => e.href)"
        )
        return [l for l in links if l and ".pdf" in l.lower()]
    except Exception:
        return []



class ASPXProvider(GTUDataProvider):
    """Playwright-based implementation of GTUDataProvider for gtu.ac.in.

    Uses the exact element IDs discovered from the live page HTML.

    Usage::

        with ASPXProvider(headless=True) as provider:
            result = provider.collect_all(progress_callback=cb)
    """

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = _TIMEOUT_MS,
        slow_mo_ms: int = 0,
    ) -> None:
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._slow_mo_ms = slow_mo_ms
        self._pw = None
        self._browser = None
        self._page = None

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "ASPXProvider":
        self._start()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def _start(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            ) from exc

        logger.info("Launching Chromium (headless=%s)", self._headless)
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(
                headless=self._headless,
                slow_mo=self._slow_mo_ms,
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception as e:
            if "executable" in str(e).lower() or "install" in str(e).lower() or "missing" in str(e).lower():
                logger.info("Playwright executable missing. Attempting automatic browser installation...")
                import subprocess
                import sys
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                self._browser = self._pw.chromium.launch(
                    headless=self._headless,
                    slow_mo=self._slow_mo_ms,
                    args=["--disable-blink-features=AutomationControlled"]
                )
            else:
                raise

        ctx = self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self._page = ctx.new_page()
        self._page.set_default_timeout(self._timeout_ms)
        self._goto_page()

    def _goto_page(self) -> None:
        """Navigate to the GTU syllabus portal."""
        logger.info("Loading %s", SYLLABUS_URL)
        self._page.goto(SYLLABUS_URL, wait_until="domcontentloaded", timeout=self._timeout_ms)
        self._page.wait_for_timeout(2000)
        logger.info("Page loaded.")

    def _reload(self) -> None:
        """Ensure the browser is on the syllabus page. Does not reset selections if already on the page to allow lightning-fast cascading."""
        try:
            if self._page and self._page.url == SYLLABUS_URL:
                logger.debug("Already on syllabus page. Keeping page state for speed.")
                return
        except Exception:
            pass

        logger.info("Performing full page reload...")
        self._page.goto(SYLLABUS_URL, wait_until="domcontentloaded", timeout=self._timeout_ms)
        self._page.wait_for_timeout(1000)

    def close(self) -> None:
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception as exc:
            logger.debug("Close error: %s", exc)
        finally:
            self._browser = None
            self._pw = None
            self._page = None

    # ── GTUDataProvider API ───────────────────────────────────────────────────

    def fetch_courses(self) -> List[Dict]:
        """Return all courses. Sourced from static HTML (no AJAX needed)."""
        return STATIC_COURSES

    def fetch_branches(self, course_id: str) -> List[Dict]:
        """Return branches for a course by selecting it and reading the branch dropdown."""
        self._reload()
        if not _select_and_wait(self._page, ID_COURSE, course_id, next_css_id=ID_BRANCH):
            return []
        opts = _get_select_options(self._page, ID_BRANCH)
        return [{"id": o["value"], "name": o["text"], "course_id": course_id} for o in opts]

    def fetch_semesters(self, course_id: str, branch_id: str) -> List[Dict]:
        """Return semesters by selecting course+branch."""
        self._reload()
        _select_and_wait(self._page, ID_COURSE, course_id, next_css_id=ID_BRANCH)
        _select_and_wait(self._page, ID_BRANCH, branch_id, next_css_id=ID_SEM)
        opts = _get_select_options(self._page, ID_SEM)
        return [{"value": o["value"], "text": o["text"]} for o in opts]

    def fetch_academic_years(self, course_id: str = "BE", branch_id: str = "07") -> List[str]:
        """Return academic years (available after branch selection)."""
        self._reload()
        _select_and_wait(self._page, ID_COURSE, course_id, next_css_id=ID_BRANCH)
        _select_and_wait(self._page, ID_BRANCH, branch_id, next_css_id=ID_YEAR)
        opts = _get_select_options(self._page, ID_YEAR)
        return [o["value"] for o in opts]

    def fetch_elective_types(self, course_id: str, branch_id: str, sem: str) -> List[str]:
        """Return elective types by selecting course+branch+semester."""
        self._reload()
        _select_and_wait(self._page, ID_COURSE, course_id, next_css_id=ID_BRANCH)
        _select_and_wait(self._page, ID_BRANCH, branch_id, next_css_id=ID_SEM)
        _select_and_wait(self._page, ID_SEM, sem, next_css_id=ID_ELECTIVE)
        opts = _get_select_options(self._page, ID_ELECTIVE)
        raw_vals = [o["value"] for o in opts]
        normalized = []
        for v in raw_vals:
            if v == "Non-Elective":
                normalized.append("Non_Elective")
            else:
                normalized.append(v)
        return normalized if normalized else ["Non_Elective", "Elective"]

    def fetch_subjects(self, course_id: str, branch_id: str, sem: str, elective_type: str, academic_year: str = "") -> List[Dict]:
        """Select all dropdowns and click Search to get subjects."""
        self._reload()
        if not _select_and_wait(self._page, ID_COURSE, course_id, next_css_id=ID_BRANCH):
            logger.error("Failed to select course: %s", course_id)
            return []
        if not _select_and_wait(self._page, ID_BRANCH, branch_id, next_css_id=ID_SEM):
            logger.error("Failed to select branch: %s", branch_id)
            return []
        
        # Select Academic Year FIRST (after Branch loads it)
        if academic_year:
            if not _select_and_wait(self._page, ID_YEAR, academic_year):
                logger.error("Failed to select academic year: %s", academic_year)
                return []
                
        # Select Semester SECOND (loads Elective)
        if not _select_and_wait(self._page, ID_SEM, sem, next_css_id=ID_ELECTIVE):
            logger.error("Failed to select semester: %s", sem)
            return []
        
        # Translate Non_Elective (underscore) to Non-Elective (hyphen) for GTU website
        gtu_elective = "Non-Elective" if elective_type == "Non_Elective" else elective_type
        if not _select_and_wait(self._page, ID_ELECTIVE, gtu_elective):
            logger.error("Failed to select elective type: %s", gtu_elective)
            return []
        return self._click_search_and_extract(course_id, branch_id, sem, elective_type, year=academic_year)

    def fetch_subjects_both_electives(self, course_id: str, branch_id: str, sem: str, academic_year: str = "") -> List[Dict]:
        """Scrape both Non_Elective and Elective in a single browser run without reloading, saving up to 10+ seconds."""
        self._reload()
        if not _select_and_wait(self._page, ID_COURSE, course_id, next_css_id=ID_BRANCH):
            logger.error("Failed to select course: %s", course_id)
            return []
        if not _select_and_wait(self._page, ID_BRANCH, branch_id, next_css_id=ID_SEM):
            logger.error("Failed to select branch: %s", branch_id)
            return []
            
        # Select Academic Year FIRST
        if academic_year:
            if not _select_and_wait(self._page, ID_YEAR, academic_year):
                logger.error("Failed to select academic year: %s", academic_year)
                return []
                
        # Select Semester SECOND (loads Elective)
        if not _select_and_wait(self._page, ID_SEM, sem, next_css_id=ID_ELECTIVE):
            logger.error("Failed to select semester: %s", sem)
            return []

        subjects = []
        # Query 1: Non-Elective
        if _select_and_wait(self._page, ID_ELECTIVE, "Non-Elective"):
            subjects += self._click_search_and_extract(course_id, branch_id, sem, "Non_Elective", year=academic_year)

        # Query 2: Elective (reuse page state, only change Elective dropdown and search)
        if _select_and_wait(self._page, ID_ELECTIVE, "Elective"):
            subjects += self._click_search_and_extract(course_id, branch_id, sem, "Elective", year=academic_year)

        return subjects

    def _click_search_and_extract(
        self, course: str, branch: str, semester: str, elective: str,
        year: str = ""
    ) -> List[Dict]:
        """Click the Search button and extract subjects from the result table."""
        try:
            # Store the old inner text of the results container if it exists
            old_text = ""
            try:
                old_text = self._page.inner_text(ID_RESULT)
            except Exception:
                pass

            self._page.click(ID_SEARCH)
            
            # Wait for AJAX to start and finish
            self._page.wait_for_timeout(100) # brief tick
            try:
                self._page.wait_for_function(
                    """([pnl, old]) => {
                        if (typeof Sys !== 'undefined' && Sys.WebForms && Sys.WebForms.PageRequestManager) {
                            if (Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostback()) {
                                return false;
                            }
                        }
                        var hasTable = pnl.querySelector('table') !== null;
                        return hasTable || pnl.innerText !== old || pnl.innerText.indexOf("No record found") !== -1;
                    }""",
                    arg=[self._page.locator(ID_RESULT).element_handle(), old_text],
                    timeout=5000
                )
            except Exception as wait_exc:
                logger.debug("Search wait timeout, extracting anyway: %s", wait_exc)
        except Exception as exc:
            logger.debug("Search click failed: %s", exc)
            return []

        subjects = _extract_subjects_from_table(
            self._page, course, branch, semester, elective, year
        )

        # Also try to get more subjects from the grid (GridView pattern)
        if not subjects:
            subjects = self._extract_from_gridview(course, branch, semester, elective, year)

        logger.info(
            "Search(%s/%s/sem=%s/%s) -> %d subjects",
            course, branch, semester, elective, len(subjects)
        )
        return subjects

    def _extract_from_gridview(self, course: str, branch: str, semester: str,
                                elective: str, year: str = "") -> List[Dict]:
        """Fallback: same as _extract_subjects_from_table but via page reference."""
        return _extract_subjects_from_table(self._page, course, branch, semester, elective, year)

    def fetch_subject_by_code(self, subject_code: str) -> List[Dict]:
        """Fetch subject details directly by entering the subject code in the text field."""
        self._reload()
        try:
            # Clear text fields first and fill the subject code field
            self._page.fill(ID_SUBCODE, subject_code)
            try:
                # Reset dropdowns by choosing index 0 to avoid conflicting filters
                self._page.select_option(ID_COURSE, index=0)
            except Exception:
                pass

            old_text = ""
            try:
                old_text = self._page.inner_text(ID_RESULT)
            except Exception:
                pass

            self._page.click(ID_SEARCH)
            
            # Wait for AJAX to start and finish
            self._page.wait_for_timeout(100) # brief tick
            try:
                self._page.wait_for_function(
                    """([pnl, old]) => {
                        if (typeof Sys !== 'undefined' && Sys.WebForms && Sys.WebForms.PageRequestManager) {
                            if (Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostback()) {
                                return false;
                            }
                        }
                        var hasTable = pnl.querySelector('table') !== null;
                        return hasTable || pnl.innerText !== old || pnl.innerText.indexOf("No record found") !== -1;
                    }""",
                    arg=[self._page.locator(ID_RESULT).element_handle(), old_text],
                    timeout=5000
                )
            except Exception as wait_exc:
                logger.debug("Live subject code search wait timeout: %s", wait_exc)
        except Exception as exc:
            logger.debug("Direct search fill/click failed: %s", exc)
            return []

        # Extract rows
        subjects = []
        try:
            rows = self._page.eval_on_selector_all(
                "#ContentPlaceHolder1_pnl tr",
                """rows => rows.map(r => ({
                    cells: Array.from(r.querySelectorAll('td')).map(c => c.innerText.trim()),
                    links: Array.from(r.querySelectorAll('a[href]')).map(a => a.href)
                }))"""
            )
            for row in rows:
                cells = row.get("cells", [])
                links = row.get("links", [])

                pdf_links = [l for l in links if l and ".pdf" in l.lower()]
                if not pdf_links or len(cells) < 16:
                    continue

                code = cells[10].strip()
                if not code or code != subject_code:
                    continue

                branch = cells[11].strip()
                row_year = cells[12].strip()
                name = cells[13].strip()
                
                # Check if it's elective
                is_elec_text = cells[2].lower()
                elective = "Elective" if "yes" in is_elec_text else "Non_Elective"
                
                sem = cells[15].strip()
                
                # Guess course based on code prefix or default to BE
                course = "BE"
                if code.startswith("37") or code.startswith("27"):
                    course = "ME"
                elif code.startswith("32") or code.startswith("22"):
                    course = "MC"
                elif code.startswith("39") or code.startswith("29"):
                    course = "MP"
                elif code.startswith("35") or code.startswith("25"):
                    course = "MB"

                subj = {
                    "subject_code": code,
                    "subject_name": name,
                    "elective_type": elective,
                    "course": course,
                    "branch": branch,
                    "semester": sem,
                    "academic_year": row_year,
                    "syllabus_pdf_url": pdf_links[0],
                    
                    # Teaching Scheme Hours
                    "lectures": cells[16].strip() if len(cells) > 16 else "0",
                    "tutorial": cells[17].strip() if len(cells) > 17 else "0",
                    "practical": cells[18].strip() if len(cells) > 18 else "0",
                    "pbl": cells[19].strip() if len(cells) > 19 else "NA",
                    "credits": cells[20].strip() if len(cells) > 20 else "0",
                    
                    # Examination Marks
                    "exam_e": cells[21].strip() if len(cells) > 21 else "0",
                    "exam_m": cells[22].strip() if len(cells) > 22 else "0",
                    "exam_i": cells[23].strip() if len(cells) > 23 else "0",
                    "exam_v": cells[24].strip() if len(cells) > 24 else "0",
                    "exam_total": cells[25].strip() if len(cells) > 25 else "0",
                    
                    # Nested Details Sub-row
                    "detail_category": cells[1].replace("Category :", "").strip() if len(cells) > 1 else "",
                    "detail_elective": cells[2].replace("Elective Subject:", "").strip() if len(cells) > 2 else "No",
                    "detail_is_theory": cells[3].replace("IsTheory :", "").strip() if len(cells) > 3 else "No",
                    "detail_theory_duration": cells[4].replace("Theory Exam Duration :", "").strip() if len(cells) > 4 else "0",
                    "detail_is_practical": cells[5].replace("IsPractical :", "").strip() if len(cells) > 5 else "No",
                    "detail_practical_duration": cells[6].replace("Practical Exam Duration :", "").strip() if len(cells) > 6 else "0",
                    "detail_remark": cells[7].replace("Remark :", "").strip() if len(cells) > 7 else "N/A",
                    "detail_is_functional": cells[8].replace("Isfunctional :", "").strip() if len(cells) > 8 else "No",
                    "detail_is_semipractical": cells[9].replace("IsSemipractical :", "").strip() if len(cells) > 9 else "No",
                }
                subjects.append(subj)
        except Exception as exc:
            logger.debug("Parsing direct subject table failed: %s", exc)

        logger.info("Direct search(%s) -> found %d subjects", subject_code, len(subjects))
        return subjects


    def fetch_subject_by_name(self, subject_name: str) -> List[Dict]:
        """Fetch subject details directly by entering the subject name in the text field."""
        self._reload()
        try:
            # Clear code field first and fill the subject name field
            self._page.fill(ID_SUBCODE, "")
            self._page.fill(ID_SUBNAME, subject_name)
            try:
                # Reset dropdowns by choosing index 0 to avoid conflicting filters
                self._page.select_option(ID_COURSE, index=0)
            except Exception:
                pass

            old_text = ""
            try:
                old_text = self._page.inner_text(ID_RESULT)
            except Exception:
                pass

            self._page.click(ID_SEARCH)
            
            # Wait for AJAX to start and finish
            self._page.wait_for_timeout(100) # brief tick
            try:
                self._page.wait_for_function(
                    """([pnl, old]) => {
                        if (typeof Sys !== 'undefined' && Sys.WebForms && Sys.WebForms.PageRequestManager) {
                            if (Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostback()) {
                                return false;
                            }
                        }
                        var hasTable = pnl.querySelector('table') !== null;
                        return hasTable || pnl.innerText !== old || pnl.innerText.indexOf("No record found") !== -1;
                    }""",
                    arg=[self._page.locator(ID_RESULT).element_handle(), old_text],
                    timeout=5000
                )
            except Exception as wait_exc:
                logger.debug("Live subject name search wait timeout: %s", wait_exc)
        except Exception as exc:
            logger.debug("Direct name search fill/click failed: %s", exc)
            return []

        # Extract rows
        subjects = []
        try:
            rows = self._page.eval_on_selector_all(
                "#ContentPlaceHolder1_pnl tr",
                """rows => rows.map(r => ({
                    cells: Array.from(r.querySelectorAll('td')).map(c => c.innerText.trim()),
                    links: Array.from(r.querySelectorAll('a[href]')).map(a => a.href)
                }))"""
            )
            for row in rows:
                cells = row.get("cells", [])
                links = row.get("links", [])

                pdf_links = [l for l in links if l and ".pdf" in l.lower()]
                if not pdf_links or len(cells) < 16:
                    continue

                code = cells[10].strip()
                if not code:
                    continue

                branch = cells[11].strip()
                row_year = cells[12].strip()
                name = cells[13].strip()
                
                # Check if it's elective
                is_elec_text = cells[2].lower()
                elective = "Elective" if "yes" in is_elec_text else "Non_Elective"
                
                sem = cells[15].strip()
                
                # Guess course based on code prefix or default to BE
                course = "BE"
                if code.startswith("37") or code.startswith("27"):
                    course = "ME"
                elif code.startswith("32") or code.startswith("22"):
                    course = "MC"
                elif code.startswith("39") or code.startswith("29"):
                    course = "MP"
                elif code.startswith("35") or code.startswith("25"):
                    course = "MB"

                subj = {
                    "subject_code": code,
                    "subject_name": name,
                    "elective_type": elective,
                    "course": course,
                    "branch": branch,
                    "semester": sem,
                    "academic_year": row_year,
                    "syllabus_pdf_url": pdf_links[0],
                    
                    # Teaching Scheme Hours
                    "lectures": cells[16].strip() if len(cells) > 16 else "0",
                    "tutorial": cells[17].strip() if len(cells) > 17 else "0",
                    "practical": cells[18].strip() if len(cells) > 18 else "0",
                    "pbl": cells[19].strip() if len(cells) > 19 else "NA",
                    "credits": cells[20].strip() if len(cells) > 20 else "0",
                    
                    # Examination Marks
                    "exam_e": cells[21].strip() if len(cells) > 21 else "0",
                    "exam_m": cells[22].strip() if len(cells) > 22 else "0",
                    "exam_i": cells[23].strip() if len(cells) > 23 else "0",
                    "exam_v": cells[24].strip() if len(cells) > 24 else "0",
                    "exam_total": cells[25].strip() if len(cells) > 25 else "0",
                    
                    # Nested Details Sub-row
                    "detail_category": cells[1].replace("Category :", "").strip() if len(cells) > 1 else "",
                    "detail_elective": cells[2].replace("Elective Subject:", "").strip() if len(cells) > 2 else "No",
                    "detail_is_theory": cells[3].replace("IsTheory :", "").strip() if len(cells) > 3 else "No",
                    "detail_theory_duration": cells[4].replace("Theory Exam Duration :", "").strip() if len(cells) > 4 else "0",
                    "detail_is_practical": cells[5].replace("IsPractical :", "").strip() if len(cells) > 5 else "No",
                    "detail_practical_duration": cells[6].replace("Practical Exam Duration :", "").strip() if len(cells) > 6 else "0",
                    "detail_remark": cells[7].replace("Remark :", "").strip() if len(cells) > 7 else "N/A",
                    "detail_is_functional": cells[8].replace("Isfunctional :", "").strip() if len(cells) > 8 else "No",
                    "detail_is_semipractical": cells[9].replace("IsSemipractical :", "").strip() if len(cells) > 9 else "No",
                }
                subjects.append(subj)
        except Exception as exc:
            logger.debug("Parsing direct subject table by name failed: %s", exc)

        logger.info("Direct name search(%s) -> found %d subjects", subject_name, len(subjects))
        return subjects


    def download_syllabus(self, subject_code: str) -> Optional[bytes]:
        """Try to download syllabus PDF for a subject code via direct URL patterns.

        GTU PDFs are hosted on S3:
          https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/{code}.pdf
        (Note: 'Syallbus' is a typo in the real S3 bucket - intentional.)
        """
        import requests as req
        patterns = [
            SYLLABUS_S3_FALLBACK_URL.format(subject_code=subject_code),
            f"https://gtu.ac.in/syllabus/{subject_code}.pdf",
            f"https://gtu.ac.in/uploads/syllabus/{subject_code}.pdf",
            f"https://gtu.ac.in/Syllabus/syllabus/{subject_code}.pdf",
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": SYLLABUS_URL,
        }
        for url in patterns:
            try:
                r = req.get(url, timeout=15, headers=headers)
                if r.status_code == 200 and r.content[:4] == b"%PDF":
                    logger.info("Downloaded syllabus for %s from %s", subject_code, url)
                    return r.content
            except Exception as exc:
                logger.debug("URL %s -> %s", url, exc)
        return None

    def collect_all(self, progress_callback=None) -> Dict[str, Any]:
        """Collect the complete GTU academic hierarchy.

        Strategy:
          For each course -> select it -> get branches
          For each branch -> get semesters + academic years + electives
          For each (sem, elective) -> click Search -> extract subject table

        Returns a nested dict keyed by course_id -> branch_id -> semester_val -> elective.
        """
        self._goto_page()
        database: Dict[str, Any] = {}
        total = 0

        for course in STATIC_COURSES:
            cid = course["id"]
            cname = course["name"]
            database[cid] = {"_meta": course, "_branches": {}}

            logger.info("=== Course: %s (%s) ===", cid, cname)

            # Get branches for this course
            self._reload()
            _select_and_wait(self._page, ID_COURSE, cid, settle_ms=2500)
            branches = _get_select_options(self._page, ID_BRANCH)

            if not branches:
                logger.info("  No branches for course %s", cid)
                continue

            for branch_opt in branches:
                bid = branch_opt["value"]
                bname = branch_opt["text"]
                database[cid]["_branches"][bid] = {"_meta": {"id": bid, "name": bname}, "_semesters": {}}
                logger.info("  Branch: %s (%s)", bid, bname)

                # Select branch to trigger semester + year + elective dropdowns
                self._reload()
                _select_and_wait(self._page, ID_COURSE, cid, settle_ms=2500)
                _select_and_wait(self._page, ID_BRANCH, bid, settle_ms=2000)

                semesters = _get_select_options(self._page, ID_SEM)
                years = _get_select_options(self._page, ID_YEAR)

                if not semesters:
                    logger.info("    No semesters found for %s/%s", cid, bid)
                    continue

                # Collect all academic years dynamically present on the portal
                valid_years = [y["value"] for y in years]
                if not valid_years:
                    valid_years = ["2018-19", "2024-25"]

                for sem_opt in semesters:
                    sem_val = sem_opt["value"]
                    sem_text = sem_opt["text"]

                    database[cid]["_branches"][bid]["_semesters"][sem_val] = {
                        "_meta": {"value": sem_val, "text": sem_text},
                        "_electives": {}
                    }

                    # Get elective types for this sem
                    self._reload()
                    _select_and_wait(self._page, ID_COURSE, cid, settle_ms=2500)
                    _select_and_wait(self._page, ID_BRANCH, bid, settle_ms=2000)
                    _select_and_wait(self._page, ID_SEM, sem_val, settle_ms=1500)

                    electives = _get_select_options(self._page, ID_ELECTIVE)
                    if not electives:
                        electives = [
                            {"value": "Non-Elective", "text": "Non-Elective"},
                            {"value": "Elective", "text": "Elective"},
                        ]

                    for elective_opt in electives:
                        elec_val = elective_opt["value"]
                        norm_elec_val = "Non_Elective" if elec_val == "Non-Elective" else elec_val
                        database[cid]["_branches"][bid]["_semesters"][sem_val]["_electives"][norm_elec_val] = []

                        for year_val in valid_years:
                            self._reload()
                            _select_and_wait(self._page, ID_COURSE, cid, settle_ms=2500)
                            _select_and_wait(self._page, ID_BRANCH, bid, settle_ms=2000)
                            _select_and_wait(self._page, ID_SEM, sem_val, settle_ms=1500)
                            if year_val:
                                _select_and_wait(self._page, ID_YEAR, year_val, settle_ms=1200)
                            _select_and_wait(self._page, ID_ELECTIVE, elec_val, settle_ms=1200)

                            subjects = self._click_search_and_extract(
                                cid, bid, sem_val, norm_elec_val, year=year_val
                            )

                            # Enrich subjects with branch name and course name
                            for s in subjects:
                                s["course_name"] = cname
                                s["branch_name"] = bname
                                s["semester_label"] = sem_text

                            # Merge without duplicates (by code + academic_year)
                            target_list = database[cid]["_branches"][bid]["_semesters"][sem_val]["_electives"][elec_val]
                            added_count = 0
                            for s in subjects:
                                if not any(
                                    x.get("subject_code") == s["subject_code"]
                                    and x.get("academic_year") == s["academic_year"]
                                    for x in target_list
                                ):
                                    target_list.append(s)
                                    added_count += 1
                            total += added_count

                            if progress_callback:
                                progress_callback({
                                    "course": cid,
                                    "branch": bid,
                                    "semester": sem_val,
                                    "elective": elec_val,
                                    "academic_year": year_val,
                                    "subjects_found": added_count,
                                    "total_so_far": total,
                                })

        logger.info("Collection complete: %d total subjects", total)
        return database
