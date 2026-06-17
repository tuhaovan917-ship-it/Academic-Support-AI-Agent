from __future__ import annotations

import json
from typing import Any

from .base import LLMError


ALLOWED_ROUTES = {
    "policy_retrieval",
    "procedure_or_form",
    "student_schedule",
    "student_grades",
    "mixed_policy_student",
    "fallback",
}

ALLOWED_TOOL_NAMES = {
    "get_student_schedule",
    "get_student_grades",
    "get_graduation_snapshot",
}


INTENT_SYSTEM_PROMPT = """You are the intent classifier and query rewriter for a HUIT academic advising RAG agent.

Return ONLY a valid JSON object. Do not answer the student's question.

Allowed routes:
- policy_retrieval: rules/policies/forms that need approved RAG evidence.
- procedure_or_form: workflows, forms, where to submit approved forms.
- student_schedule: personal schedule lookup; requires student_id.
- student_grades: personal GPA, grades, failed courses; requires student_id.
- mixed_policy_student: needs both personal student data and policy evidence.
- fallback: outside approved data, unsupported, or unsafe to answer.

Safety rules:
- If the query asks BM09, QD-3230, QD-3297, QD-2658, scholarship, tuition, finance, contact directory, or student discipline details from pending data, route fallback.
- Prefer QD-3344 current policy for graduation, grades, GPA, study time, warnings, and ranking.
- Rewrite retrieval_query in Vietnamese with the exact article/table keywords when possible.
- Do not invent student data.

JSON schema:
{
  "route": "policy_retrieval",
  "intent": "grade_conversion",
  "needs_retrieval": true,
  "needs_tool": false,
  "tool_name": null,
  "retrieval_intent": "current_policy",
  "retrieval_query": "Điều 30 Bảng 3 quy đổi thang điểm 10 thang điểm 4 điểm chữ",
  "pending_slots": [],
  "notes": [],
  "confidence": 0.85,
  "reason": "short reason"
}
"""


def build_intent_user_prompt(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_intent_json(content: str, *, raw_provider: str, model: str | None = None) -> dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError("invalid_intent_json") from exc
    if not isinstance(data, dict):
        raise LLMError("intent_payload_not_object")
    route = data.get("route")
    if route not in ALLOWED_ROUTES:
        raise LLMError(f"invalid_intent_route:{route}")
    tool_name = data.get("tool_name")
    if tool_name is not None and tool_name not in ALLOWED_TOOL_NAMES:
        raise LLMError(f"invalid_intent_tool:{tool_name}")
    confidence = data.get("confidence", 0)
    if not isinstance(confidence, (int, float)):
        confidence = 0
    return {
        "route": route,
        "intent": _string_or_default(data.get("intent"), "general"),
        "needs_retrieval": bool(data.get("needs_retrieval")),
        "needs_tool": bool(data.get("needs_tool")),
        "tool_name": tool_name,
        "retrieval_intent": _string_or_default(data.get("retrieval_intent"), "current_policy"),
        "retrieval_query": _optional_string(data.get("retrieval_query")),
        "pending_slots": _string_list(data.get("pending_slots")),
        "notes": _string_list(data.get("notes")),
        "confidence": float(confidence),
        "reason": _string_or_default(data.get("reason"), ""),
        "raw": {"provider": raw_provider, "model": model},
    }


def _string_or_default(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _optional_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
