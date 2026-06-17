from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ERR_MISSING_QUERY = "ERR_MISSING_QUERY"
ERR_MISSING_MSSV = "ERR_MISSING_MSSV"
ERR_STUDENT_NOT_FOUND = "ERR_STUDENT_NOT_FOUND"
ERR_POLICY_NOT_FOUND = "ERR_POLICY_NOT_FOUND"
ERR_LLM_TIMEOUT = "ERR_LLM_TIMEOUT"
ERR_LLM_PROVIDER_FAILED = "ERR_LLM_PROVIDER_FAILED"
ERR_VECTOR_DB_UNAVAILABLE = "ERR_VECTOR_DB_UNAVAILABLE"
ERR_UNSUPPORTED_OR_LOW_CONFIDENCE_INTENT = "ERR_UNSUPPORTED_OR_LOW_CONFIDENCE_INTENT"
ERR_PENDING_OR_DISCARDED_SOURCE = "ERR_PENDING_OR_DISCARDED_SOURCE"
ERR_STUDENT_API_UNAVAILABLE = "ERR_STUDENT_API_UNAVAILABLE"
ERR_INTERNAL = "ERR_INTERNAL"


@dataclass
class ServiceError:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


def error_from_agent(agent_payload: dict[str, Any]) -> ServiceError | None:
    status = agent_payload.get("status")
    critic = agent_payload.get("critic") or {}
    warnings = list(critic.get("warnings") or [])
    errors = list(critic.get("errors") or [])
    llm = agent_payload.get("llm") or {}

    if agent_payload.get("needs_clarification") and "student_id" in warnings:
        return ServiceError(ERR_MISSING_MSSV, "Cần MSSV để tra cứu dữ liệu cá nhân.", {"warnings": warnings})
    if "student_not_found" in errors:
        return ServiceError(ERR_STUDENT_NOT_FOUND, "Không tìm thấy sinh viên trong nguồn dữ liệu.", {"errors": errors})
    if "missing_tool_result" in errors or any(item.startswith("tool_error:") for item in errors):
        return ServiceError(ERR_STUDENT_API_UNAVAILABLE, "Không nhận được dữ liệu từ công cụ tra cứu sinh viên.", {"errors": errors})
    if "missing_citation" in errors:
        return ServiceError(ERR_POLICY_NOT_FOUND, "Không tìm thấy căn cứ đã duyệt phù hợp.", {"errors": errors})
    if any("pending_or_discarded" in item for item in warnings + errors):
        return ServiceError(
            ERR_PENDING_OR_DISCARDED_SOURCE,
            "Nguồn liên quan đang pending hoặc đã bị loại khỏi nguồn hiện hành.",
            {"warnings": warnings, "errors": errors},
        )
    if any("unsupported_or_low_confidence_intent" in item for item in warnings + errors):
        return ServiceError(
            ERR_UNSUPPORTED_OR_LOW_CONFIDENCE_INTENT,
            "Chưa đủ căn cứ hoặc chưa xác định được ý định câu hỏi.",
            {"warnings": warnings, "errors": errors},
        )
    llm_error = str(llm.get("error") or "")
    if "timeout" in llm_error.lower():
        return ServiceError(ERR_LLM_TIMEOUT, "LLM bị timeout và hệ thống đã fallback.", {"llm_error": llm_error})
    if llm_error:
        return ServiceError(ERR_LLM_PROVIDER_FAILED, "LLM lỗi và hệ thống đã fallback.", {"llm_error": llm_error})
    if status == "fallback":
        return ServiceError(ERR_INTERNAL, "Agent fallback vì chưa đủ điều kiện trả lời.", {"warnings": warnings, "errors": errors})
    return None
