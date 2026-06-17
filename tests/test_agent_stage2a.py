from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["LLM_PROVIDER"] = "mock"
os.environ["MOCK_LLM_MODE"] = "template"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import run_agent


def assert_answered(response) -> None:
    assert response.status == "answered", response.to_dict()
    assert response.critic["passed"], response.to_dict()


def test_policy_retrieval_graduation_condition() -> None:
    response = run_agent("Điều kiện xét tốt nghiệp của sinh viên HUIT là gì?", session_id="test_policy")
    assert_answered(response)
    assert response.route == "policy_retrieval"
    assert response.citations
    assert any("Điều 39" in citation for citation in response.citations)
    assert response.llm["provider"] == "mock"


def test_form_retrieval_graduation_application() -> None:
    response = run_agent("Muốn xét tốt nghiệp thì dùng biểu mẫu nào?", session_id="test_form")
    assert_answered(response)
    assert response.route == "procedure_or_form"
    assert "BM12" in response.answer
    assert response.citations


def test_schedule_requires_student_id_then_uses_memory() -> None:
    session_id = "test_clarification"
    first = run_agent("Lịch học hôm nay của em?", session_id=session_id)
    assert first.status == "need_clarification"
    assert first.needs_clarification
    assert "MSSV" in first.answer
    assert first.llm == {}

    second = run_agent("SV001", session_id=session_id)
    assert_answered(second)
    assert second.route == "student_schedule"
    assert second.student_id == "SV001"
    assert "TP101" in second.answer


def test_grades_tool_with_student_id() -> None:
    response = run_agent("GPA của SV003 bao nhiêu?", session_id="test_grades")
    assert_answered(response)
    assert response.route == "student_grades"
    assert response.tool_results["cumulative_gpa"] == 1.86
    assert "1.86" in response.answer


def test_mixed_graduation_student_with_failed_courses() -> None:
    response = run_agent("SV002 còn nợ môn thì có được xét tốt nghiệp không?", session_id="test_mixed_failed")
    assert_answered(response)
    assert response.route == "mixed_policy_student"
    assert response.tool_results["eligible_for_graduation"] is False
    assert "chưa đủ điều kiện" in response.answer
    assert response.citations


def test_mixed_graduation_retake_warning() -> None:
    response = run_agent("SV004 học lại nhiều thì xếp loại giỏi có bị ảnh hưởng không?", session_id="test_retake")
    assert_answered(response)
    assert "5%" in response.answer
    assert "Điều 40" in response.answer or any("Điều 40" in citation for citation in response.citations)


def test_mixed_graduation_missing_certificates() -> None:
    response = run_agent("SV005 có được công nhận tốt nghiệp không?", session_id="test_missing_cert")
    assert_answered(response)
    assert response.tool_results["eligible_for_graduation"] is False
    assert "foreign_language" in response.answer or "gdtc" in response.answer


def test_unknown_student_fallback() -> None:
    response = run_agent("GPA của SV999 bao nhiêu?", session_id="test_unknown_student")
    assert response.status == "fallback"
    assert "student_not_found" in response.critic["errors"]


def test_out_of_scope_fallback() -> None:
    response = run_agent("Trường bán áo hoodie ở đâu?", session_id="test_fallback")
    assert response.status == "fallback"
    assert response.route == "fallback"


def main() -> int:
    tests = [
        test_policy_retrieval_graduation_condition,
        test_form_retrieval_graduation_application,
        test_schedule_requires_student_id_then_uses_memory,
        test_grades_tool_with_student_id,
        test_mixed_graduation_student_with_failed_courses,
        test_mixed_graduation_retake_warning,
        test_mixed_graduation_missing_certificates,
        test_unknown_student_fallback,
        test_out_of_scope_fallback,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
