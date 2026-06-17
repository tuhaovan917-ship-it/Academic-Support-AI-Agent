from __future__ import annotations

import os
import sys
from pathlib import Path


os.environ["LLM_PROVIDER"] = "mock"
os.environ["MOCK_LLM_MODE"] = "template"
os.environ["HYBRID_PLANNER_MODE"] = "auto"
os.environ["STUDENT_API_PROVIDER"] = "mock"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import AgentService, AgentServiceRequest


def test_policy_contract_compact_response() -> None:
    response = AgentService().ask(
        AgentServiceRequest(
            query="Điểm A là từ mấy đến mấy?",
            session_id="service_policy",
        )
    )
    payload = response.to_dict()
    assert payload["status"] == "answered"
    assert payload["route"] == "policy_retrieval"
    assert payload["citations"]
    assert "retrieval_results" not in payload
    assert "critic" not in payload


def test_debug_response_can_include_internal_fields() -> None:
    response = AgentService().ask(
        AgentServiceRequest(
            query="Điểm A là từ mấy đến mấy?",
            session_id="service_debug",
            include_debug=True,
        )
    )
    payload = response.to_dict()
    assert payload["status"] == "answered"
    assert "retrieval_results" in payload
    assert "critic" in payload
    assert "planner" in payload


def test_empty_query_returns_error_code() -> None:
    response = AgentService().ask({"query": "", "session_id": "service_empty"})
    payload = response.to_dict()
    assert payload["status"] == "fallback"
    assert payload["error"]["code"] == "ERR_MISSING_QUERY"
    assert payload["needs_clarification"]


def test_clarification_session_flow() -> None:
    service = AgentService()
    first = service.ask({"query": "Lịch học hôm nay của em?", "session_id": "service_clarify"})
    assert first.status == "need_clarification"
    assert first.error and first.error["code"] == "ERR_MISSING_MSSV"

    second = service.ask({"query": "SV001", "session_id": "service_clarify"})
    payload = second.to_dict()
    assert payload["status"] == "answered"
    assert payload["route"] == "student_schedule"
    assert payload["tool_results"]["student_id"] == "SV001"


def test_tool_response_contract() -> None:
    response = AgentService().ask({"query": "GPA của SV003 bao nhiêu?", "session_id": "service_tool"})
    payload = response.to_dict()
    assert payload["status"] == "answered"
    assert payload["route"] == "student_grades"
    assert payload["tool_results"]["cumulative_gpa"] == 1.86


def test_boundary_response_error_code() -> None:
    response = AgentService().ask({"query": "QĐ-3297 còn áp dụng cho chuẩn CNTT không?", "session_id": "service_boundary"})
    payload = response.to_dict()
    assert payload["status"] == "fallback"
    assert payload["error"]["code"] == "ERR_PENDING_OR_DISCARDED_SOURCE"


def test_http_student_client_config_error_surfaces_as_service_error() -> None:
    old_provider = os.environ.get("STUDENT_API_PROVIDER")
    old_base_url = os.environ.get("STUDENT_API_BASE_URL")
    os.environ["STUDENT_API_PROVIDER"] = "http"
    os.environ["STUDENT_API_BASE_URL"] = ""
    try:
        response = AgentService().ask({"query": "GPA của SV003 bao nhiêu?", "session_id": "service_http_missing_url"})
        payload = response.to_dict()
        assert payload["status"] == "fallback"
        assert payload["error"]["code"] == "ERR_STUDENT_API_UNAVAILABLE"
    finally:
        if old_provider is None:
            os.environ.pop("STUDENT_API_PROVIDER", None)
        else:
            os.environ["STUDENT_API_PROVIDER"] = old_provider
        if old_base_url is None:
            os.environ.pop("STUDENT_API_BASE_URL", None)
        else:
            os.environ["STUDENT_API_BASE_URL"] = old_base_url


def main() -> int:
    tests = [
        test_policy_contract_compact_response,
        test_debug_response_can_include_internal_fields,
        test_empty_query_returns_error_code,
        test_clarification_session_flow,
        test_tool_response_contract,
        test_boundary_response_error_code,
        test_http_student_client_config_error_surfaces_as_service_error,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
