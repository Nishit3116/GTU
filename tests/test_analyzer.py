"""Unit tests for GTU Multi-Category AI Paper Analyzer Module."""

from pathlib import Path
from gtu_academic_engine.analyzer.analyzer_engine import GTUPaperAnalyzer


def test_parse_questions_from_text():
    analyzer = GTUPaperAnalyzer()
    sample_text = """
    Q.1 (a) Explain 7-layer OSI Reference Model in detail with diagram. [07]
    Q.1 (b) Differentiate between TCP and UDP protocols. [04]
    Q.1 (c) Define bandwidth and throughput. [03]
    Q.2 (a) Describe Dijkstra Shortest Path routing algorithm. [07]
    """
    questions = analyzer.parse_questions_from_text(sample_text)
    assert len(questions) >= 3
    assert any(q["marks"] == 7 for q in questions)
    assert any(q["marks"] == 4 for q in questions)
    assert any(q["marks"] == 3 for q in questions)


def test_analyze_paper_pdf_rule_engine(tmp_path):
    analyzer = GTUPaperAnalyzer()
    res = analyzer.analyze_paper_pdf(
        pdf_path=Path("nonexistent.pdf"),
        subject_code="3170719",
        subject_name="Design and Analysis of Algorithms"
    )
    assert res["status"] == "success"
    assert res["subject_code"] == "3170719"
    assert "chapter_breakdown" in res
    assert len(res["chapter_breakdown"]) == 5
    assert "marks_breakdown" in res
    assert "predicted_questions" in res
    assert len(res["predicted_questions"]) >= 3
