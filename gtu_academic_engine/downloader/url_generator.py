from typing import List


def generate_url(session: str, course: str, subject_code: str) -> str:
    return f"https://gtu.ac.in/uploads/{session}/{course}/{subject_code}.pdf"


def generate_urls(sessions: List[str], course: str, subject_code: str) -> List[str]:
    return [generate_url(s, course, subject_code) for s in sessions]
