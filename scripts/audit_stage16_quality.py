from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORRECTED_DIR = PROJECT_ROOT / "data" / "review" / "ocr_corrected"
CORRECTIONS_DIR = PROJECT_ROOT / "data" / "review" / "ocr_corrections"
REPORT_PATH = PROJECT_ROOT / "data" / "review" / "stage16_quality_report.md"
DECISIONS_PATH = PROJECT_ROOT / "data" / "review" / "stage16_source_decisions.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def article_numbers(sections: list[str] | None) -> list[str]:
    numbers: list[str] = []
    for section in sections or []:
        match = re.search(r"\d+", section)
        if match:
            numbers.append(match.group(0))
    return unique_preserve_order(numbers)


def assess_document(doc_id: str, markdown: str, meta: dict[str, Any]) -> dict[str, Any]:
    generated = article_numbers(meta.get("generated_sections"))
    pending = article_numbers(meta.get("pending_sections"))
    needs_pdf_count = markdown.count("[NEEDS_PDF_VERIFICATION]")
    unverified_count = markdown.count("[UNVERIFIED")
    raw_table_draft = "Raw OCR Table Drafts" in markdown
    can_vectorize = meta.get("can_vectorize") is True
    review_status = meta.get("review_status")

    issues: list[str] = []
    if can_vectorize:
        issues.append("can_vectorize is true, but Stage 16 expects pending drafts only")
    if review_status != "draft_ocr_structured":
        issues.append(f"unexpected review_status: {review_status}")
    if needs_pdf_count == 0:
        issues.append("missing NEEDS_PDF_VERIFICATION marker")
    if not generated:
        issues.append("no article sections detected")
    if doc_id == "huit_qd_3230_foreign_language_outcomes_2023" and not raw_table_draft:
        issues.append("foreign-language source should expose raw OCR table drafts")
    if doc_id == "huit_qd_2658_student_affairs_2023" and not pending:
        issues.append("student-affairs source should record pending sections")

    if doc_id == "huit_qd_3297_it_outcomes_2023":
        readiness = "ready_for_manual_correction"
        priority = 1
        recommendation = "Correct this first from the PDF because it is only 3 pages and has a small article set."
    elif doc_id == "huit_qd_3230_foreign_language_outcomes_2023":
        readiness = "needs_pdf_visual_review"
        priority = 2
        recommendation = "Correct after QD-3297; focus on tables and threshold values before any vectorization."
    else:
        readiness = "needs_pdf_visual_review"
        priority = 3
        recommendation = "Correct last or in batches; start with high-impact student-affairs and discipline articles."

    safe_for_vector = False
    if issues:
        readiness = "not_safe_for_vector"

    return {
        "document_id": doc_id,
        "readiness": readiness,
        "manual_correction_priority": priority,
        "safe_for_vector": safe_for_vector,
        "generated_articles": generated,
        "pending_articles": pending,
        "needs_pdf_markers": needs_pdf_count,
        "unverified_markers": unverified_count,
        "has_raw_table_draft": raw_table_draft,
        "issues": issues,
        "recommendation": recommendation,
    }


def collect_assessments() -> list[dict[str, Any]]:
    assessments: list[dict[str, Any]] = []
    for meta_path in sorted(CORRECTED_DIR.glob("*.meta.yaml")):
        doc_id = meta_path.name.removesuffix(".meta.yaml")
        markdown_path = CORRECTED_DIR / f"{doc_id}.md"
        if not markdown_path.exists():
            assessments.append(
                {
                    "document_id": doc_id,
                    "readiness": "not_safe_for_vector",
                    "manual_correction_priority": 99,
                    "safe_for_vector": False,
                    "generated_articles": [],
                    "pending_articles": [],
                    "needs_pdf_markers": 0,
                    "unverified_markers": 0,
                    "has_raw_table_draft": False,
                    "issues": ["missing markdown output"],
                    "recommendation": "Regenerate Stage 15 output.",
                }
            )
            continue
        assessments.append(assess_document(doc_id, markdown_path.read_text(encoding="utf-8"), load_yaml(meta_path)))
    return sorted(assessments, key=lambda item: item["manual_correction_priority"])


def render_report(assessments: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage 16 Quality Report",
        "",
        "## Scope",
        "",
        "Stage 16 checks the OCR structured drafts created in Stage 15. It does not rebuild the vector DB and does not approve any pending source for current-policy answers.",
        "",
        "## Summary",
        "",
        "| Source | Readiness | Safe for vector? | Generated articles | Pending articles | Main recommendation |",
        "|---|---|---:|---|---|---|",
    ]
    for item in assessments:
        lines.append(
            "| {doc} | `{readiness}` | `{safe}` | {generated} | {pending} | {rec} |".format(
                doc=item["document_id"],
                readiness=item["readiness"],
                safe=str(item["safe_for_vector"]).lower(),
                generated=", ".join(item["generated_articles"]) or "-",
                pending=", ".join(item["pending_articles"]) or "-",
                rec=item["recommendation"],
            )
        )

    lines.extend(["", "## Per-Source Findings", ""])
    for item in assessments:
        lines.extend(
            [
                f"### {item['document_id']}",
                "",
                f"- Readiness: `{item['readiness']}`",
                f"- Manual correction priority: `{item['manual_correction_priority']}`",
                f"- Safe for vector: `{str(item['safe_for_vector']).lower()}`",
                f"- Generated articles: {', '.join(item['generated_articles']) or '-'}",
                f"- Pending articles: {', '.join(item['pending_articles']) or '-'}",
                f"- NEEDS_PDF_VERIFICATION markers: `{item['needs_pdf_markers']}`",
                f"- UNVERIFIED markers: `{item['unverified_markers']}`",
                f"- Raw OCR table draft present: `{str(item['has_raw_table_draft']).lower()}`",
                "",
                "Issues:",
            ]
        )
        if item["issues"]:
            lines.extend(f"- {issue}" for issue in item["issues"])
        else:
            lines.append("- No structural issue found in the Stage 15 draft. Legal PDF verification is still required.")
        lines.extend(["", f"Recommendation: {item['recommendation']}", ""])

    lines.extend(
        [
            "## Decision",
            "",
            "No source is approved for vectorization in Stage 16.",
            "",
            "Recommended Stage 17 order:",
            "",
            "1. Manually correct `huit_qd_3297_it_outcomes_2023` against the PDF.",
            "2. Manually correct `huit_qd_3230_foreign_language_outcomes_2023`, with special attention to threshold tables.",
            "3. Manually correct `huit_qd_2658_student_affairs_2023` in batches, prioritizing student discipline and high-impact support articles.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def write_decisions(assessments: list[dict[str, Any]]) -> None:
    payload = {
        "stage": 16,
        "decision": "no_vectorization_yet",
        "db_rebuild_required": False,
        "audit_retrieval_required": False,
        "next_stage": "manual_pdf_correction",
        "sources": {
            item["document_id"]: {
                "readiness": item["readiness"],
                "manual_correction_priority": item["manual_correction_priority"],
                "safe_for_vector": item["safe_for_vector"],
                "generated_articles": item["generated_articles"],
                "pending_articles": item["pending_articles"],
                "issues": item["issues"],
                "recommendation": item["recommendation"],
            }
            for item in assessments
        },
    }
    DECISIONS_PATH.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> int:
    assessments = collect_assessments()
    REPORT_PATH.write_text(render_report(assessments), encoding="utf-8")
    write_decisions(assessments)
    print(f"Wrote {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {DECISIONS_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
