from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import run_agent


def _set_mock(mode: str = "template") -> None:
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["MOCK_LLM_MODE"] = mode


def assert_answered(response) -> None:
    assert response.status == "answered", response.to_dict()
    assert response.critic["passed"], response.to_dict()


def test_mock_llm_template_path_keeps_stage2a_behavior() -> None:
    _set_mock("template")
    response = run_agent("Muốn xét tốt nghiệp thì dùng biểu mẫu nào?", session_id="stage2b_template")
    assert_answered(response)
    assert response.llm["provider"] == "mock"
    assert response.llm["used"] is True
    assert response.llm["fallback_used"] is False
    assert "BM12" in response.answer


def test_mock_llm_json_path_can_generate_from_payload() -> None:
    _set_mock("json")
    response = run_agent("Điều kiện xét tốt nghiệp của sinh viên HUIT là gì?", session_id="stage2b_json")
    assert_answered(response)
    assert response.llm["provider"] == "mock"
    assert response.citations


def test_malformed_llm_falls_back_to_template() -> None:
    _set_mock("malformed")
    response = run_agent("Điều kiện xét tốt nghiệp của sinh viên HUIT là gì?", session_id="stage2b_malformed")
    assert_answered(response)
    assert response.llm["fallback_used"] is True
    assert response.llm["error"] == "mock_malformed_response"
    assert response.citations


def test_fake_citation_llm_falls_back_to_template() -> None:
    _set_mock("fake_citation")
    response = run_agent("Điều kiện xét tốt nghiệp của sinh viên HUIT là gì?", session_id="stage2b_fake_citation")
    assert_answered(response)
    assert response.llm["fallback_used"] is True
    assert response.llm["error"].startswith("invalid_llm_citation")


def test_unknown_provider_falls_back_to_template() -> None:
    os.environ["LLM_PROVIDER"] = "unknown_provider"
    response = run_agent("Điều kiện xét tốt nghiệp của sinh viên HUIT là gì?", session_id="stage2b_unknown_provider")
    assert_answered(response)
    assert response.llm["fallback_used"] is True
    assert response.llm["error"].startswith("unsupported_llm_provider")


def test_clarification_does_not_call_llm() -> None:
    _set_mock("error")
    response = run_agent("Lịch học hôm nay của em?", session_id="stage2b_no_llm_for_clarification")
    assert response.status == "need_clarification"
    assert response.llm == {}


def test_hybrid_planner_rescues_ambiguous_grade_policy() -> None:
    _set_mock("template")
    os.environ["HYBRID_PLANNER_MODE"] = "auto"
    response = run_agent("Điểm A là từ mấy đến mấy?", session_id="stage2b_hybrid_grade_a")
    assert_answered(response)
    assert response.route == "policy_retrieval"
    assert response.planner["mode"] in {"hybrid_llm", "rule"}
    assert response.llm["provider"] == "deterministic"
    assert "8.5" in response.answer
    assert "Điều 30" in response.answer or any("Điều 30" in citation for citation in response.citations)


def test_hybrid_planner_can_be_forced_to_always_call_llm() -> None:
    _set_mock("template")
    os.environ["HYBRID_PLANNER_MODE"] = "always"
    response = run_agent("Điều kiện xét tốt nghiệp là gì?", session_id="stage2b_hybrid_always")
    assert_answered(response)
    assert response.planner["mode"] == "hybrid_llm"
    assert response.planner["provider"] == "mock"
    assert response.citations


def main() -> int:
    tests = [
        test_mock_llm_template_path_keeps_stage2a_behavior,
        test_mock_llm_json_path_can_generate_from_payload,
        test_malformed_llm_falls_back_to_template,
        test_fake_citation_llm_falls_back_to_template,
        test_unknown_provider_falls_back_to_template,
        test_clarification_does_not_call_llm,
        test_hybrid_planner_rescues_ambiguous_grade_policy,
        test_hybrid_planner_can_be_forced_to_always_call_llm,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
