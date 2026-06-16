"""
GTU Academic Engine Constants

Centralized configuration for URLs, element IDs, and static data.
"""

# ── GTU Portal URLs ─────────────────────────────────────────────────────────

SYLLABUS_PORTAL_URL = "https://gtu.ac.in/syllabus/syllabus.aspx"
"""Main GTU syllabus portal for cascading subject/branch/semester selection."""

SYLLABUS_DIRECT_URL = "https://gtu.ac.in/uploads/{session}/BE/{subject_code}.pdf"
"""Direct URL pattern for syllabus PDFs on GTU uploads."""

SYLLABUS_S3_FALLBACK_URL = "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/{subject_code}.pdf"
"""S3 fallback for syllabus when direct URL fails (typo 'Syallbus' is intentional from GTU)."""

PYQ_DIRECT_URL = "https://gtu.ac.in/uploads/{session}/BE/{subject_code}.pdf"
"""Direct URL pattern for PYQ PDFs on GTU uploads."""

PYQ_REPOSITORY_URL = "https://gtu.ac.in/Download1.aspx"
"""GTU repository page for downloading PYQs via alternative method."""

# ── ASPX Portal Element IDs ─────────────────────────────────────────────────
# Verified 2026-06-14 from live GTU portal

ASPX_COURSE_SELECT = "#ContentPlaceHolder1_ddcourse"
"""ASPX element ID for course/program selection dropdown."""

ASPX_BRANCH_SELECT = "#ContentPlaceHolder1_ddlbrcode"
"""ASPX element ID for branch selection (populated after course)."""

ASPX_SEMESTER_SELECT = "#ContentPlaceHolder1_ddsem"
"""ASPX element ID for semester selection (populated after branch)."""

ASPX_YEAR_SELECT = "#ContentPlaceHolder1_ddl_effFrom"
"""ASPX element ID for academic year selection (populated after branch)."""

ASPX_ELECTIVE_SELECT = "#ContentPlaceHolder1_ddl_iselective"
"""ASPX element ID for elective type (populated after semester)."""

ASPX_SUBJECT_CODE_INPUT = "#ContentPlaceHolder1_txtsubcode"
"""ASPX element ID for subject code text input."""

ASPX_SUBJECT_NAME_INPUT = "#ContentPlaceHolder1_txtsubjectname"
"""ASPX element ID for subject name text input."""

ASPX_SEARCH_BUTTON = "#ContentPlaceHolder1_btn_search"
"""ASPX element ID for search button to submit query."""

ASPX_RESULTS_PANEL = "#ContentPlaceHolder1_pnl"
"""ASPX element ID for results panel containing search results table."""

# ── Course Codes ────────────────────────────────────────────────────────────

COURSE_CODES = {
    "IB": "Applied Science- IB",
    "CS": "Applied Science-CS",
    "DB": "Applied Science-DB",
    "IM": "Applied Science-IM",
    "EP": "Bachelor of Engineering (Part Time)",
    "BE": "Bachelor of Engineering",
    "ME": "Master of Engineering",
}
"""Mapping of course IDs to course names."""

DEFAULT_COURSE = "BE"
"""Default course code (Bachelor of Engineering)."""

# ── Default Session Order ───────────────────────────────────────────────────

DEFAULT_SESSIONS = [
    "W2026", "S2026",  # 2026
    "W2025", "S2025",  # 2025
    "W2024", "S2024",  # 2024
    "W2023", "S2023",  # 2023
    "W2022", "S2022",  # 2022
    "W2021", "S2021",  # 2021
]
"""Default list of PYQ sessions (Winter/Summer pairs, most recent first)."""

SESSION_PATTERNS = {
    "winter": r"W\d{4}",
    "summer": r"S\d{4}",
}
"""Regex patterns for identifying session types."""

# ── Error Categories ───────────────────────────────────────────────────────

class DownloadError:
    """Error status codes for categorizing download failures."""
    
    NOT_FOUND = 404
    """PDF file does not exist at the URL (file removed or wrong subject code)."""
    
    FORBIDDEN = 403
    """Access denied or rate-limited (temporary block, may recover with retry)."""
    
    TIMEOUT = "timeout"
    """Connection timeout (network issue or server slow)."""
    
    INVALID_PDF = "invalid_pdf"
    """File downloaded but is not a valid PDF (corrupt or wrong format)."""
    
    NETWORK_ERROR = "network_error"
    """Network connectivity issue (no internet or DNS failure)."""
    
    UNKNOWN = "unknown"
    """Unknown or unexpected error."""

# ── Timeouts (seconds) ──────────────────────────────────────────────────────

REQUEST_TIMEOUT_DEFAULT = 15.0
"""Default timeout for HTTP requests (seconds)."""

REQUEST_TIMEOUT_SHORT = 5.0
"""Short timeout for quick health checks."""

BROWSER_TIMEOUT = 30.0
"""Timeout for Playwright browser operations."""

# ── Retry Configuration ─────────────────────────────────────────────────────

MAX_RETRIES_DEFAULT = 3
"""Default maximum retry attempts for failed downloads."""

RETRY_BACKOFF_SECONDS = 1.0
"""Base backoff time between retries (exponential backoff applies)."""

# ── File Patterns ───────────────────────────────────────────────────────────

PDF_MAGIC_BYTES = b"%PDF"
"""Magic bytes that identify a valid PDF file."""

VALID_PDF_MIN_SIZE = 1024
"""Minimum file size for a valid PDF (bytes)."""
