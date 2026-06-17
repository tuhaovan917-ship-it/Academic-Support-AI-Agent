from __future__ import annotations

import re
import unicodedata

from .models import PlannerDecision


STUDENT_ID_RE = re.compile(r"\b(?:SV)?\d{3,6}\b", re.IGNORECASE)


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-zA-Z0-9%]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def extract_student_id(query: str) -> str | None:
    match = STUDENT_ID_RE.search(query or "")
    if not match:
        return None
    raw = match.group(0).upper()
    return raw if raw.startswith("SV") else f"SV{raw}"


def plan(query: str, student_id: str | None = None, pending_route: str | None = None) -> PlannerDecision:
    normalized = normalize_text(query)
    has_student_id = bool(student_id)

    if pending_route and has_student_id and len(normalized.split()) <= 3:
        return _decision_for_pending_route(pending_route, has_student_id=True)

    asks_schedule = any(term in normalized for term in ("lich hoc", "thoi khoa bieu", "hom nay hoc", "tuan nay hoc"))
    asks_grade = any(term in normalized for term in ("gpa", "diem", "mon no", "rot mon", "no mon", "ket qua hoc tap"))
    asks_graduation = any(term in normalized for term in ("tot nghiep", "xet tot nghiep", "cong nhan tot nghiep"))
    asks_graduation_ranking = any(term in normalized for term in ("xep loai", "gioi", "xuat sac", "hoc lai", "5%"))
    asks_form = any(term in normalized for term in ("bieu mau", "phieu", "mau nao", "don nao", "dung mau", "dung phieu"))
    asks_procedure = any(term in normalized for term in ("quy trinh", "thu tuc", "lam the nao", "nop o dau", "rut hoc phan", "huy hoc phan", "chuyen nganh"))
    asks_policy = any(
        term in normalized
        for term in (
            "quy dinh",
            "dieu kien",
            "canh bao",
            "buoc thoi hoc",
            "xep loai",
            "tin chi",
            "hoc lai",
            "diem i",
            "phuc khao",
            "qd 3344",
        )
    )

    if asks_schedule:
        return _tool_decision("student_schedule", "get_student_schedule", has_student_id)

    if (asks_graduation or asks_graduation_ranking) and (
        asks_grade
        or has_student_id
        or any(term in normalized for term in ("em", "minh", "toi", "con no", "duoc khong", "sv"))
    ):
        return _mixed_decision(has_student_id)

    if asks_grade:
        return _tool_decision("student_grades", "get_student_grades", has_student_id)

    if asks_form or asks_procedure:
        return PlannerDecision(
            route="procedure_or_form",
            needs_retrieval=True,
            retrieval_intent="procedure",
        )

    if asks_graduation or asks_policy:
        return PlannerDecision(route="policy_retrieval", needs_retrieval=True, retrieval_intent="current_policy")

    return PlannerDecision(
        route="fallback",
        notes=["unsupported_or_low_confidence_intent"],
    )


def _decision_for_pending_route(pending_route: str, has_student_id: bool) -> PlannerDecision:
    if pending_route == "student_schedule":
        return _tool_decision("student_schedule", "get_student_schedule", has_student_id)
    if pending_route == "student_grades":
        return _tool_decision("student_grades", "get_student_grades", has_student_id)
    if pending_route in {"student_graduation", "mixed_policy_student"}:
        return _mixed_decision(has_student_id)
    return PlannerDecision(route="fallback")


def _tool_decision(route: str, tool_name: str, has_student_id: bool) -> PlannerDecision:
    if not has_student_id:
        return PlannerDecision(
            route=route,  # type: ignore[arg-type]
            needs_tool=True,
            tool_name=tool_name,
            pending_slots=["student_id"],
            clarification_questions=["Bạn cho mình biết MSSV để tra cứu dữ liệu cá nhân được không?"],
        )
    return PlannerDecision(route=route, needs_tool=True, tool_name=tool_name)  # type: ignore[arg-type]


def _mixed_decision(has_student_id: bool) -> PlannerDecision:
    if not has_student_id:
        return PlannerDecision(
            route="mixed_policy_student",
            needs_retrieval=True,
            needs_tool=True,
            tool_name="get_graduation_snapshot",
            pending_slots=["student_id"],
            clarification_questions=["Bạn cho mình biết MSSV để mình đối chiếu dữ liệu cá nhân với quy định tốt nghiệp nhé."],
        )
    return PlannerDecision(
        route="mixed_policy_student",
        needs_retrieval=True,
        needs_tool=True,
        tool_name="get_graduation_snapshot",
        retrieval_intent="current_policy",
    )
