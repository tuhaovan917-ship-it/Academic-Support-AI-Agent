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
    if decision.needs_tool and tool_result.get("error") == "student_not_found":
        errors.append("student_not_found")

    for item in retrieval_results:
        if item.get("document_id") in PENDING_OR_DISCARDED_DOCS:
            errors.append(f"uses_pending_or_discarded_source:{item.get('document_id')}")

    lower_answer = answer.lower()
    if "xếp loại" in lower_answer or "xep loai" in lower_answer or "giỏi" in lower_answer or "xuất sắc" in lower_answer:
        if "5%" not in answer and "Điều 40" not in answer:
            warnings.append("graduation_ranking_without_5_percent_warning")

    if decision.route in {"student_graduation", "mixed_policy_student"}:
        if not any("Điều 39" in citation or "Điều 40" in citation or "Điều 41" in citation for citation in citations):
            warnings.append("graduation_answer_without_article_39_40_41_citation")

    return {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
    }
