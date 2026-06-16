"""GTU Academic Data Exporter.

Exports the collected academic dataset to CSV, XLSX, and a plain-text report.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def export_csv(subjects: List[Dict], dest: Path) -> Path:
    """Export flat subject list to a CSV file.

    Args:
        subjects: List of subject dicts from collector result['subjects']
        dest: Destination file path (will be created with parents)

    Returns:
        Path to the written CSV file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not subjects:
        logger.warning("No subjects to export to CSV.")
        dest.write_text("", encoding="utf-8")
        return dest

    # Canonical field order
    fieldnames = [
        "subject_code", "subject_name", "course", "course_name",
        "branch", "branch_name", "semester", "semester_label",
        "elective_type", "academic_year",
    ]
    # Ensure all keys present (fill missing with empty string)
    all_keys = {k for s in subjects for k in s.keys()}
    extra = sorted(all_keys - set(fieldnames))
    fieldnames.extend(extra)

    with dest.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for subj in subjects:
            row = {f: subj.get(f, "") for f in fieldnames}
            writer.writerow(row)

    logger.info("Exported %d subjects to CSV: %s", len(subjects), dest)
    return dest


def export_xlsx(subjects: List[Dict], dest: Path) -> Path:
    """Export flat subject list to an XLSX file.

    Requires openpyxl.  Falls back gracefully if not installed.

    Args:
        subjects: List of subject dicts from collector result['subjects']
        dest: Destination file path (.xlsx)

    Returns:
        Path to the written XLSX file.

    Raises:
        ImportError: If openpyxl is not installed.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for XLSX export. Run: pip install openpyxl"
        ) from exc

    dest.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "GTU Subjects"

    if not subjects:
        ws.append(["No data collected"])
        wb.save(dest)
        return dest

    fieldnames = [
        "subject_code", "subject_name", "course", "course_name",
        "branch", "branch_name", "semester", "semester_label",
        "elective_type", "academic_year",
    ]
    all_keys = {k for s in subjects for k in s.keys()}
    extra = sorted(all_keys - set(fieldnames))
    fieldnames.extend(extra)

    # Header row styling
    header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)

    ws.append(fieldnames)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Data rows — alternate row shading
    alt_fill = PatternFill(start_color="EEF2F7", end_color="EEF2F7", fill_type="solid")
    for idx, subj in enumerate(subjects, start=2):
        row = [subj.get(f, "") for f in fieldnames]
        ws.append(row)
        if idx % 2 == 0:
            for cell in ws[idx]:
                cell.fill = alt_fill

    # Auto-fit column widths (approximate)
    for col_idx, col_name in enumerate(fieldnames, start=1):
        max_len = max(
            (len(str(subj.get(col_name, "") or "")) for subj in subjects),
            default=0,
        )
        width = min(max(max_len, len(col_name)) + 4, 50)
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Freeze header row
    ws.freeze_panes = "A2"

    wb.save(dest)
    logger.info("Exported %d subjects to XLSX: %s", len(subjects), dest)
    return dest


def export_report(result: Dict[str, Any], dest: Path) -> Path:
    """Write a human-readable collector report text file.

    Args:
        result: Full collector result dict (database + subjects + stats)
        dest: Destination .txt file path

    Returns:
        Path to the written report file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    stats = result.get("stats", {})
    subjects = result.get("subjects", [])

    courses = sorted({s.get("course", "") for s in subjects if s.get("course")})
    branches = sorted({s.get("branch", "") for s in subjects if s.get("branch")})
    semesters = sorted({str(s.get("semester", "")) for s in subjects if s.get("semester")})
    electives = sorted({s.get("elective_type", "") for s in subjects if s.get("elective_type")})

    lines = [
        "GTU Academic Data — Collector Report",
        "=" * 50,
        f"Generated      : {_utc_now()}",
        f"Status         : {'Success' if stats.get('success') else 'Failed'}",
        f"Elapsed        : {stats.get('elapsed_seconds', '?')} seconds",
        "",
        "Summary",
        "-" * 30,
        f"Courses        : {len(courses)}",
        f"Branches       : {len(branches)}",
        f"Semesters      : {len(semesters)}",
        f"Elective Types : {len(electives)}",
        f"Total Subjects : {len(subjects)}",
        f"Errors         : {stats.get('errors', 0)}",
        "",
        "Courses",
        "-" * 30,
    ]
    for c in courses:
        lines.append(f"  {c}")

    lines += ["", "Branches", "-" * 30]
    for b in branches:
        lines.append(f"  {b}")

    lines += ["", "Elective Types", "-" * 30]
    for e in electives:
        lines.append(f"  {e}")

    lines += [
        "",
        "=" * 50,
        "End of Report",
    ]

    dest.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Written collector report to %s", dest)
    return dest


def export_all(result: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
    """Run all three exports (CSV, XLSX, report) into output_dir.

    Returns a dict mapping format name → output path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    subjects = result.get("subjects", [])

    paths: Dict[str, Path] = {}

    csv_path = export_csv(subjects, output_dir / "subjects.csv")
    paths["csv"] = csv_path

    try:
        xlsx_path = export_xlsx(subjects, output_dir / "subjects.xlsx")
        paths["xlsx"] = xlsx_path
    except ImportError:
        logger.warning("Skipping XLSX export — openpyxl not installed.")

    report_path = export_report(result, output_dir / "collector_report.txt")
    paths["report"] = report_path

    return paths
