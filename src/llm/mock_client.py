from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

from .base import LLMError, LLMResponse


class MockLLMClient:
    provider_name = "mock"

    def generate_answer(self, payload: dict[str, Any]) -> LLMResponse:
        mode = os.environ.get("MOCK_LLM_MODE", "template").lower()
        if mode == "error":
            raise LLMError("mock_provider_error")
        if mode == "malformed":
            raise LLMError("mock_malformed_response")
        if mode == "fake_citation":
            return LLMResponse(
                answer="Câu trả lời mock có trích dẫn không hợp lệ.",
                used_citations=["QĐ giả, Điều 999"],
                raw={"mode": mode},
            )
        if mode == "json":
            citations = list(payload.get("allowed_citations", []))
            return LLMResponse(
                answer=payload.get("template_answer") or "Mock LLM answer.",
                used_citations=citations[:1],
                raw={"mode": mode},
            )
        return LLMResponse(
            answer=payload.get("template_answer") or "",
            used_citations=list(payload.get("template_citations", [])),
            raw={"mode": mode, "template_passthrough": True},
        )

    def classify_intent(self, payload: dict[str, Any]) -> dict[str, Any]:
        mode = os.environ.get("MOCK_LLM_MODE", "template").lower()
        if mode == "error":
            raise LLMError("mock_provider_error")
        query = str(payload.get("query") or "")
        normalized = _normalize(query)
        if any(term in normalized for term in ("qd 3297", "qd 3230", "qd 2658", "bm09", "hoan thi", "hoc bong", "hoc phi")):
            return _decision("fallback", "blocked_or_missing_source", notes=["missing_or_blocked_source:pending_or_discarded"])
        if _asks_grade_conversion(normalized):
            return _decision(
                "policy_retrieval",
                "grade_conversion",
                needs_retrieval=True,
                retrieval_query="Điều 30 Bảng 3 quy đổi thang điểm 10 thang điểm 4 điểm chữ A B C D F",
                reason="grade conversion query",
            )
        if "lich hoc" in normalized or "thoi khoa bieu" in normalized:
            return _decision("student_schedule", "student_schedule", needs_tool=True, tool_name="get_student_schedule")
        if "gpa" in normalized or "diem cua" in normalized:
            return _decision("student_grades", "student_grades", needs_tool=True, tool_name="get_student_grades")
        if "tot nghiep" in normalized and any(term in normalized for term in ("em", "sv", "duoc khong", "minh")):
            return _decision(
                "mixed_policy_student",
                "mixed_graduation",
                needs_retrieval=True,
                needs_tool=True,
                tool_name="get_graduation_snapshot",
                retrieval_query="Điều 39 điều kiện xét tốt nghiệp công nhận tốt nghiệp",
            )
        if "tot nghiep" in normalized:
            return _decision(
                "policy_retrieval",
                "graduation_conditions",
                needs_retrieval=True,
                retrieval_query="Điều 39 điều kiện xét tốt nghiệp công nhận tốt nghiệp BM12",
            )
        return _decision("fallback", "out_of_scope", notes=["unsupported_or_low_confidence_intent"])


def _decision(
    route: str,
    intent: str,
    *,
    needs_retrieval: bool = False,
    needs_tool: bool = False,
    tool_name: str | None = None,
    retrieval_query: str | None = None,
    notes: list[str] | None = None,
    reason: str = "mock intent",
) -> dict[str, Any]:
    return {
        "route": route,
        "intent": intent,
        "needs_retrieval": needs_retrieval,
        "needs_tool": needs_tool,
        "tool_name": tool_name,
        "retrieval_intent": "current_policy",
        "retrieval_query": retrieval_query,
        "pending_slots": [],
        "notes": notes or [],
        "confidence": 0.9,
        "reason": reason,
        "raw": {"provider": "mock"},
    }


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("đ", "d").replace("Đ", "D")
    text = re.sub(r"[^a-zA-Z0-9%+.,]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _asks_grade_conversion(normalized: str) -> bool:
    has_score = bool(re.search(r"\b\d{1,2}(?:[.,]\d+)?\b", normalized))
    asks_letter_band = bool(re.search(r"\bdiem\s*(a|b\+|b|c\+|c|d\+|d|f)\b", normalized)) or bool(
        re.search(r"\b(a|b\+|b|c\+|c|d\+|d|f)\b", normalized)
    )
    return (
        "diem chu" in normalized
        or "he 4" in normalized
        or "he so 4" in normalized
        or "he so 10" in normalized
        or (has_score and any(term in normalized for term in ("doi", "sang", "tuong duong")))
        or (
            asks_letter_band
            and "diem" in normalized
            and any(term in normalized for term in ("bao nhieu", "tu may", "may diem", "la may"))
        )
    )
