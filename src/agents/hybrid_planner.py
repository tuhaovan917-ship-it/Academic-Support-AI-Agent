from __future__ import annotations

import os
from typing import Any

from src.llm import LLMError, get_llm_client

from .models import PlannerDecision
from .planner import normalize_text, plan as rule_plan


BLOCKING_NOTES = {
    "missing_or_blocked_source:pending_or_discarded",
    "missing_data:finance_or_department_contact",
}

PERSONAL_GRADE_HINTS = (
    "gpa",
    "diem cua",
    "diem em",
    "diem minh",
    "diem toi",
    "mon no",
    "rot mon",
    "no mon",
    "ket qua hoc tap cua",
)


def plan(query: str, student_id: str | None = None, pending_route: str | None = None) -> PlannerDecision:
    base = rule_plan(query, student_id=student_id, pending_route=pending_route)
    base.planner_meta = {
        "mode": "rule",
        "hybrid_enabled": _hybrid_enabled(),
        "rule_route": base.route,
        "rule_intent": base.intent,
    }

    if not _hybrid_enabled():
        return base
    if _has_blocking_note(base):
        base.planner_meta.update({"hybrid_skipped": "rule_guard_blocked"})
        return base
    if base.pending_slots and pending_route:
        base.planner_meta.update({"hybrid_skipped": "clarification_continuation"})
        return base
    if _planner_mode() == "off":
        base.planner_meta.update({"hybrid_skipped": "mode_off"})
        return base
    if _planner_mode() == "auto" and _rule_is_high_confidence(base, query, student_id):
        base.planner_meta.update({"hybrid_skipped": "high_confidence_rule"})
        return base

    try:
        client = get_llm_client()
        llm_decision = client.classify_intent(_intent_payload(query, student_id, base))
        decision = _decision_from_llm(llm_decision, query=query, student_id=student_id, rule_decision=base)
        decision.planner_meta = {
            "mode": "hybrid_llm",
            "provider": client.provider_name,
            "rule_route": base.route,
            "rule_intent": base.intent,
            "llm_route": llm_decision.get("route"),
            "llm_intent": llm_decision.get("intent"),
            "confidence": llm_decision.get("confidence"),
            "reason": llm_decision.get("reason"),
            "raw": llm_decision.get("raw", {}),
        }
        return decision
    except LLMError as exc:
        base.planner_meta.update(
            {
                "mode": "rule_after_llm_error",
                "llm_error": str(exc),
            }
        )
        return base


def _hybrid_enabled() -> bool:
    return os.environ.get("HYBRID_PLANNER_ENABLED", "1").strip().lower() not in {"0", "false", "no"}


def _planner_mode() -> str:
    mode = os.environ.get("HYBRID_PLANNER_MODE", "auto").strip().lower()
    return mode if mode in {"auto", "always", "off"} else "auto"


def _min_confidence() -> float:
    try:
        return float(os.environ.get("HYBRID_PLANNER_MIN_CONFIDENCE", "0.65"))
    except ValueError:
        return 0.65


def _has_blocking_note(decision: PlannerDecision) -> bool:
    return any(note in BLOCKING_NOTES for note in decision.notes)


def _rule_is_high_confidence(decision: PlannerDecision, query: str, student_id: str | None) -> bool:
    normalized = normalize_text(query)
    if decision.route in {"student_schedule", "mixed_policy_student"}:
        return True
    if decision.route == "student_grades":
        return bool(student_id) or any(term in normalized for term in PERSONAL_GRADE_HINTS)
    if decision.route == "policy_retrieval":
        return bool(decision.retrieval_query) and decision.intent not in {"general"}
    if decision.route == "procedure_or_form":
        return bool(decision.retrieval_query and decision.retrieval_query != query)
    if decision.route == "fallback":
        return False
    return False


def _intent_payload(query: str, student_id: str | None, rule_decision: PlannerDecision) -> dict[str, Any]:
    return {
        "query": query,
        "normalized_query": normalize_text(query),
        "student_id_present": bool(student_id),
        "rule_decision": {
            "route": rule_decision.route,
            "intent": rule_decision.intent,
            "needs_retrieval": rule_decision.needs_retrieval,
            "needs_tool": rule_decision.needs_tool,
            "retrieval_query": rule_decision.retrieval_query,
            "notes": rule_decision.notes,
        },
        "current_primary_source": "QĐ-3344/QĐ-DCT ngày 05/09/2025",
        "blocked_sources": [
            "BM09 pending/HUFI old domain",
            "QĐ-3230 discarded",
            "QĐ-3297 historical/old",
            "QĐ-2658 pending OCR review",
        ],
    }


def _decision_from_llm(
    llm_decision: dict[str, Any],
    *,
    query: str,
    student_id: str | None,
    rule_decision: PlannerDecision,
) -> PlannerDecision:
    confidence = float(llm_decision.get("confidence") or 0)
    if confidence < _min_confidence():
        fallback = rule_decision
        fallback.notes = list(dict.fromkeys([*fallback.notes, "llm_intent_low_confidence"]))
        return fallback

    route = llm_decision["route"]
    if (
        student_id
        and rule_decision.needs_tool
        and rule_decision.route in {"student_schedule", "student_grades", "mixed_policy_student"}
        and route != rule_decision.route
    ):
        fallback = rule_decision
        fallback.notes = list(dict.fromkeys([*fallback.notes, "llm_intent_preserved_tool_route"]))
        return fallback
    needs_tool = bool(llm_decision.get("needs_tool"))
    tool_name = llm_decision.get("tool_name")
    if route in {"student_schedule", "student_grades", "mixed_policy_student"}:
        needs_tool = True
        tool_name = _tool_name_for_route(route)
    if route in {"student_schedule", "student_grades"}:
        llm_decision["needs_retrieval"] = False
        llm_decision["retrieval_query"] = None
    pending_slots = list(llm_decision.get("pending_slots") or [])
    clarification_questions: list[str] = []
    if needs_tool and not student_id and route in {"student_schedule", "student_grades", "mixed_policy_student"}:
        pending_slots = list(dict.fromkeys([*pending_slots, "student_id"]))
        clarification_questions = [_clarification_for_route(route)]

    if route == "fallback":
        notes = list(llm_decision.get("notes") or ["unsupported_or_low_confidence_intent"])
        return PlannerDecision(route="fallback", intent=llm_decision.get("intent", "fallback"), notes=notes)

    return PlannerDecision(
        route=route,
        needs_retrieval=bool(llm_decision.get("needs_retrieval")),
        needs_tool=needs_tool,
        tool_name=tool_name,
        retrieval_intent=llm_decision.get("retrieval_intent") or "current_policy",
        retrieval_query=llm_decision.get("retrieval_query") or _fallback_retrieval_query(route, query),
        intent=llm_decision.get("intent") or "general",
        pending_slots=pending_slots,
        clarification_questions=clarification_questions,
        notes=list(llm_decision.get("notes") or []),
    )


def _clarification_for_route(route: str) -> str:
    if route == "mixed_policy_student":
        return "Bạn cho mình biết MSSV để mình đối chiếu dữ liệu cá nhân với quy định học vụ nhé."
    return "Bạn cho mình biết MSSV để tra cứu dữ liệu cá nhân được không?"


def _fallback_retrieval_query(route: str, query: str) -> str | None:
    if route == "policy_retrieval":
        return query
    if route == "procedure_or_form":
        return query
    if route == "mixed_policy_student":
        return "Điều 39 điều kiện xét tốt nghiệp công nhận tốt nghiệp"
    return None


def _tool_name_for_route(route: str) -> str:
    if route == "student_schedule":
        return "get_student_schedule"
    if route == "student_grades":
        return "get_student_grades"
    return "get_graduation_snapshot"
