"""Interactive hierarchical subject selector for the GTU Academic Engine.

Guides the user through:
    Course → Branch → Academic Year → Semester → Elective Type → Subject

Uses cached data from gtu_academic_data.json (populated by AcademicCollector).
Supports numbered list selection and fuzzy search for subjects.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# ── Fuzzy helpers ─────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _fuzzy_score(query: str, text: str) -> int:
    """Return a simple fuzzy match score (higher = better match)."""
    q = _normalize(query)
    t = _normalize(text)
    if not q:
        return 0
    if q == t:
        return 100
    if q in t:
        return 80
    # Check all query chars appear in order
    idx = 0
    for ch in q:
        pos = t.find(ch, idx)
        if pos == -1:
            return 0
        idx = pos + 1
    # score by density
    return max(10, 60 - (len(t) - len(q)))


def _search_subjects(subjects: List[Dict], query: str, top_n: int = 30) -> List[Dict]:
    """Return subjects matching query by fuzzy name or exact code match."""
    q = query.strip()
    if not q:
        return subjects

    scored = []
    for s in subjects:
        code_score = 100 if q == s.get("subject_code", "") else (
            50 if q in s.get("subject_code", "") else 0
        )
        name_score = _fuzzy_score(q, s.get("subject_name", ""))
        best = max(code_score, name_score)
        if best > 0:
            scored.append((best, s))

    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:top_n]]


# ── Display helpers ───────────────────────────────────────────────────────────

def _divider(ch: str = "-", width: int = 50) -> None:
    print(ch * width)


def _print_numbered(items: List[str], title: str = "") -> None:
    if title:
        print(f"\n{title}")
        _divider()
    for i, item in enumerate(items, 1):
        print(f"  {i:3d}. {item}")
    _divider()


def _pick_from_list(items: List[str], prompt: str, allow_back: bool = True) -> Optional[int]:
    """Ask user to pick an item by number.

    Returns:
        0-based index, or None if user chose 'back'/0.
    """
    suffix = "  (0 = back)" if allow_back else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if raw == "" or raw == "0":
            return None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return idx
        print(f"  Please enter 1–{len(items)} or 0 to go back.")


# ── Selector ──────────────────────────────────────────────────────────────────

class SubjectSelector:
    """Guides the user from cached academic data to a chosen subject dict.

    Usage::

        cache = CacheManager()
        selector = SubjectSelector(cache)
        subject = selector.run()
        if subject:
            print(subject["subject_code"])
    """

    def __init__(self, cache) -> None:
        """
        Args:
            cache: CacheManager instance with load_academic_data() available.
        """
        self._cache = cache
        self._data: Optional[Dict] = None

    def _load(self) -> bool:
        """Load academic data from cache; return True if successful."""
        self._data = self._cache.load_academic_data()
        if not self._data:
            return False
        if not self._data.get("subjects"):
            return False
        return True

    def run(self) -> Optional[Dict]:
        """Run the full selection flow.

        Returns:
            Subject dict on success, None if user exits/cancels.
        """
        if not self._load():
            print("\n  ⚠  No academic data in cache.")
            print("     Run Option 4 (Refresh GTU Academic Data) first.\n")
            return None

        subjects: List[Dict] = self._data["subjects"]

        # Step 1: Course
        course = self._select_level(
            subjects, "course", "course_name", "Select Course"
        )
        if course is None:
            return None

        filtered = [s for s in subjects if s.get("course") == course]

        # Step 2: Branch
        branch = self._select_level(
            filtered, "branch", "branch_name", f"Select Branch  [{course}]"
        )
        if branch is None:
            return None

        filtered = [s for s in filtered if s.get("branch") == branch]

        # Step 3: Semester
        sem = self._select_level(
            filtered, "semester", "semester_label",
            f"Select Semester  [{course} / {branch}]"
        )
        if sem is None:
            return None

        filtered = [s for s in filtered if str(s.get("semester", "")) == str(sem)]

        # Step 4: Academic Year (optional — not always present)
        years = sorted({str(s.get("academic_year", "")) for s in filtered if s.get("academic_year")})
        if years:
            year = self._select_plain(years, f"Select Academic Year  [{course} / {branch} / Sem {sem}]")
            if year is None:
                return None
            filtered = [s for s in filtered if str(s.get("academic_year", "")) == year]
        else:
            year = None

        # Step 5: Elective Type
        elective_title = f"Select Elective Type  [{course} / {branch} / Sem {sem}"
        if year:
            elective_title += f" / {year}]"
        else:
            elective_title += "]"

        elective = self._select_level(
            filtered, "elective_type", "elective_type",
            elective_title
        )
        if elective is None:
            return None

        filtered = [s for s in filtered if s.get("elective_type") == elective]

        # Step 6: Subject (with search support)
        subject = self._select_subject(filtered)
        return subject

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _select_level(
        self,
        subjects: List[Dict],
        key: str,
        label_key: str,
        title: str,
    ) -> Optional[str]:
        """Select a unique value from a field across subjects."""
        # Build ordered unique list preserving first-seen order
        seen = {}
        for s in subjects:
            val = s.get(key)
            if val and val not in seen:
                seen[val] = s.get(label_key) or str(val)

        if not seen:
            print(f"  No options available for {title}.")
            return None

        if len(seen) == 1:
            only = next(iter(seen.keys()))
            print(f"\n  Auto-selected {title}: {seen[only]}")
            return only

        items = list(seen.keys())
        labels = [f"{seen[v]}  ({v})" if seen[v] != v else v for v in items]
        _print_numbered(labels, title=title)
        idx = _pick_from_list(labels, "Enter number")
        if idx is None:
            return None
        return items[idx]

    def _select_plain(self, values: List[str], title: str) -> Optional[str]:
        """Select from a plain list of string values."""
        if not values:
            return None
        if len(values) == 1:
            print(f"\n  Auto-selected: {values[0]}")
            return values[0]
        _print_numbered(values, title=title)
        idx = _pick_from_list(values, "Enter number")
        if idx is None:
            return None
        return values[idx]

    def _select_subject(self, subjects: List[Dict]) -> Optional[Dict]:
        """Subject selection with fuzzy search support."""
        if not subjects:
            print("  No subjects found for this selection.")
            return None

        print(f"\nSelect Subject  ({len(subjects)} available)")
        _divider()
        print("  Type a number to select, or type a search query, or 0 to go back.")
        _divider()

        current_list = subjects[:]
        self._show_subjects(current_list)

        while True:
            raw = input("\nEnter number or search: ").strip()

            if raw == "0" or raw == "":
                return None

            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(current_list):
                    chosen = current_list[idx]
                    self._confirm_subject(chosen)
                    return chosen
                print(f"  Enter 1–{len(current_list)} or a search term.")
                continue

            # Search
            results = _search_subjects(subjects, raw)
            if not results:
                print("  No matches found. Try a different search.")
                continue

            print(f"\n  Found {len(results)} match(es) for '{raw}':")
            current_list = results
            self._show_subjects(current_list)

    @staticmethod
    def _show_subjects(subjects: List[Dict], max_display: int = 40) -> None:
        displayed = subjects[:max_display]
        for i, s in enumerate(displayed, 1):
            code = s.get("subject_code", "?")
            name = s.get("subject_name", "?")
            sem = s.get("semester", "")
            elective = s.get("elective_type", "")
            print(f"  {i:3d}. [{code}] {name}  (Sem {sem}, {elective})")
        if len(subjects) > max_display:
            print(f"  ... and {len(subjects) - max_display} more. Narrow with search.")
        _divider()

    @staticmethod
    def _confirm_subject(subject: Dict) -> None:
        print("\n" + "-" * 50)
        print("  Selected Subject:")
        print(f"    Code    : {subject.get('subject_code', '?')}")
        print(f"    Name    : {subject.get('subject_name', '?')}")
        print(f"    Course  : {subject.get('course_name', subject.get('course', '?'))}")
        print(f"    Branch  : {subject.get('branch_name', subject.get('branch', '?'))}")
        print(f"    Semester: {subject.get('semester_label', subject.get('semester', '?'))}")
        print(f"    Elective: {subject.get('elective_type', '?')}")
        print("-" * 50)
