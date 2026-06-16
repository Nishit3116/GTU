from typing import List, Dict, Optional
import logging
from ..models.schema import Course, Branch, Subject
from .gtu_data_provider import GTUDataProvider

# Try to import existing v1 package; make optional to avoid hard failure
try:
    from gtu_pyq_downloader.config import GTUPYQConfig as V1Config
    from gtu_pyq_downloader.services.repository import GTUPaperRepositoryClient
    V1_AVAILABLE = True
except Exception:
    V1_AVAILABLE = False


class V1ProviderAdapter(GTUDataProvider):
    """Adapter that exposes v1 configuration and repository features
    through the GTUDataProvider interface. This provides a minimal bridge
    so the V2 engine can reuse v1 behaviour without rewriting it.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._logger = logger or logging.getLogger("v1_adapter")
        if V1_AVAILABLE:
            self._v1config = V1Config()
            self._repo = GTUPaperRepositoryClient(self._v1config, self._logger)
            self._repo.bootstrap()
        else:
            self._v1config = None
            self._repo = None
            self._logger.warning("v1 provider not available; adapter will return minimal stubs")

    def fetch_courses(self) -> List[Dict]:
        if not V1_AVAILABLE:
            return [Course(id="BE", name="Bachelor of Engineering").__dict__]
        return [Course(id=self._v1config.course_code, name=self._v1config.course_code).__dict__]

    def fetch_branches(self, course_id: str) -> List[Dict]:
        # v1 doesn't expose branches; return a best-effort stub
        return [Branch(id=course_id, name=course_id, course_id=course_id).__dict__]

    def fetch_semesters(self, course_id: str, branch_id: str) -> List[Dict]:
        return [1, 2, 3, 4, 5, 6, 7, 8]

    def fetch_academic_years(self, course_id: str = "BE", branch_id: str = "07") -> List[str]:
        if not V1_AVAILABLE:
            return []
        years = set()
        for s in self._v1config.sessions:
            # strip leading W/S
            years.add(s[1:])
        return sorted(list(years), reverse=True)

    def fetch_elective_types(self, course_id: str, branch_id: str, sem: str) -> List[str]:
        return ["Non_Elective", "Elective"]

    def fetch_subjects(self, course_id: str, branch_id: str, sem: str, elective_type: str) -> List[Dict]:
        # Attempt to parse <option> elements from the repository page to build a subjects list.
        # This is best-effort: if v1 repository page contains a dropdown for subjects, extract it.
        if not V1_AVAILABLE or not self._repo:
            return []

        try:
            r = self._repo._session.get(self._v1config.repository_url, timeout=self._v1config.request_timeout)
            text = r.text
        except Exception as exc:
            self._logger.warning("Failed to fetch repository page for subjects: %s", exc)
            return []

        # simple regex to capture option values: <option value="3170719">Theory of Computation</option>
        import re

        pattern = re.compile(r"<option[^>]+value=[\"']?([^\"'>\s]+)[\"']?[^>]*>([^<]+)</option>", re.IGNORECASE)
        matches = pattern.findall(text)
        subjects: List[Dict] = []
        for val, label in matches:
            # heuristic: numeric-looking values are likely subject codes
            if val.isdigit() or (val.replace(' ', '').isdigit()):
                subjects.append({
                    "subject_code": val.strip(),
                    "subject_name": label.strip(),
                    "elective_type": elective_type,
                    "course": course_id,
                    "branch": branch_id,
                    "semester": sem,
                })

        # de-duplicate by code
        seen = set()
        uniq = []
        for s in subjects:
            if s["subject_code"] in seen:
                continue
            seen.add(s["subject_code"])
            uniq.append(s)

        return uniq

    def download_syllabus(self, subject_code: str) -> Optional[bytes]:
        if not V1_AVAILABLE or not self._repo:
            return None
        # v1 repository client can attempt to discover exact repository link for a session;
        # there's no direct syllabus endpoint, so return None for now.
        return None

    def close(self) -> None:
        if self._repo:
            self._repo.close()
