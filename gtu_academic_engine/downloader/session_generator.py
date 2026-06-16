from typing import List


def generate_sessions(from_year: int, to_year: int, order: str = "winter-first") -> List[str]:
    """Generate session identifiers between two years.

    Example output (winter-first): ['W2026','S2026','W2025','S2025',...]
    """
    sessions = []
    if from_year > to_year:
        from_year, to_year = to_year, from_year

    years = list(range(to_year, from_year - 1, -1))

    for y in years:
        if order == "winter-first":
            sessions.append(f"W{y}")
            sessions.append(f"S{y}")
        else:
            sessions.append(f"S{y}")
            sessions.append(f"W{y}")
    return sessions
