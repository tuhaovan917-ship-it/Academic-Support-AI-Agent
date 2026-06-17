from __future__ import annotations

from typing import Any

from .models import PlannerDecision


PENDING_OR_DISCARDED_DOCS = {
    "huit_form_bm09_exam_postponement",
    "huit_qd_2658_student_affairs_2023",
    "huit_qd_3297_it_outcomes_2023",
    "huit_qd_3230_foreign_language_outcomes_2023",
}


def critique(
    decision: PlannerDecision,
    answer: str,
    citations: list[str],
    retrieval_results: list[dict[str, Any]],
    tool_result: dict[str, Any],
    student_id: str | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if decision.needs_retrieval and not citations:
        errors.append("missing_citation")
    if decision.needs_tool and not student_id:
        errors.append("missing_student_id")
    if decision.needs_tool and student_id and not tool_result:
        errors.append("missing_tool_result")
    tool_error = tool_result.get("error")
    if decision.needs_tool and tool_error == "student_not_found":
        errors.append("student_not_found")
    elif decision.needs_tool and tool_error:
        errors.append(f"tool_error:{tool_error}")

    for item in retrieval_results:
        if item.get("document_id") in PENDING_OR_DISCARDED_DOCS:
            errors.append(f"uses_pending_or_discarded_source:{item.get('document_id')}")

    lower_answer = answer.lower()
    if "3230" in lower_answer:
        errors.append("mentions_discarded_qd3230")
    if decision.route == "mixed_policy_student":
        if _mentions_unverified_personal_discipline(lower_answer, tool_result):
            errors.append("llm_invented_personal_discipline_or_criminal_status")

    if (
        decision.intent in {"graduation_ranking", "mixed_graduation"}
        and _mentions_ranking(lower_answer)
        and "5%" not in answer
        and "Điều 40" not in answer
    ):
        warnings.append("graduation_ranking_without_5_percent_warning")

    if decision.route in {"student_graduation", "mixed_policy_student"}:
        if not any("Điều 39" in citation or "Điều 40" in citation or "Điều 41" in citation for citation in citations):
            warnings.append("graduation_answer_without_article_39_40_41_citation")

    return {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
    }


def _mentions_ranking(lower_answer: str) -> bool:
    return any(
        term in lower_answer
        for term in (
            "xếp loại",
            "xep loai",
            "giỏi",
            "gioi",
            "xuất sắc",
            "xuat sac",
        )
    )


def _mentions_unverified_personal_discipline(lower_answer: str, tool_result: dict[str, Any]) -> bool:
    warnings = set(tool_result.get("warnings") or [])
    mentions_criminal = "truy cứu trách nhiệm hình sự" in lower_answer
    personal_discipline_markers = (
        "sinh viên bị kỷ luật",
        "sv bị kỷ luật",
        "đang bị kỷ luật",
        "đang trong thời gian bị kỷ luật",
        "bị đình chỉ học tập",
    )
    mentions_personal_discipline = any(marker in lower_answer for marker in personal_discipline_markers)
    if mentions_criminal:
        return True
    if mentions_personal_discipline and "disciplinary_warning" not in warnings:
        return True
    return False
