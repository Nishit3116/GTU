from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class Course:
    id: str
    name: str


@dataclass
class Branch:
    id: str
    name: str
    course_id: str


@dataclass
class Subject:
    subject_code: str
    subject_name: str
    elective_type: str
    course: str
    branch: Optional[str]
    semester: Optional[int]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Metadata:
    course: str
    branch: Optional[str]
    semester: Optional[str]
    academic_year: Optional[str]
    elective_type: Optional[str]
    subject_name: str
    subject_code: str
    from_year: int
    to_year: int
    merge_order: str
    session_order: str
    downloaded: List[str]
    missing: List[str]
    execution_time: float
    created_at: str = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict:
        return asdict(self)
