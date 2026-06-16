from typing import List, Dict, Optional, Any


class GTUDataProvider:
    """Abstraction layer for fetching GTU academic data.

    Implementations must provide methods to fetch courses, branches,
    semesters, academic years, elective types, subjects and subject codes.

    All methods should be idempotent and return simple serializable structures
    (lists/dicts) so they can be cached by the CacheManager.
    """

    def fetch_courses(self) -> List[Dict]:
        raise NotImplementedError()

    def fetch_branches(self, course_id: str) -> List[Dict]:
        raise NotImplementedError()

    def fetch_semesters(self, course_id: str, branch_id: str) -> List[Dict]:
        raise NotImplementedError()

    def fetch_academic_years(self, course_id: str = "BE", branch_id: str = "07") -> List[str]:
        raise NotImplementedError()

    def fetch_elective_types(self, course_id: str, branch_id: str, sem: str) -> List[str]:
        raise NotImplementedError()

    def fetch_subjects(self, course_id: str, branch_id: str, sem: str, elective_type: str, academic_year: str = "") -> List[Dict]:
        raise NotImplementedError()

    def download_syllabus(self, subject_code: str) -> Optional[bytes]:
        raise NotImplementedError()

    def collect_all(self, progress_callback=None) -> Dict[str, Any]:
        """Collect the full GTU academic hierarchy and return it as a nested dict.

        Implementations should drive all cascading dropdowns, extract subjects
        at every leaf node, and aggregate results.  progress_callback(info_dict)
        is called after each leaf node is processed.
        """
        raise NotImplementedError()
