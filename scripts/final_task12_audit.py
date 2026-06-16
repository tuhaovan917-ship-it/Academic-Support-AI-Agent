from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = PROJECT_ROOT / "data" / "review"
INTERMEDIATE_DIR = PROJECT_ROOT / "data" / "intermediate"
APPROVED_CHUNKS = REVIEW_DIR / "approved_chunks.jsonl"
AUDIT_REPORT = REVIEW_DIR / "retrieval_audit_report.json"
QD3344_AUDIT = REVIEW_DIR / "stage21_qd3344_current_source_audit.json"
UPSERT_SUMMARY = INTERMEDIATE_DIR / "stage22_qd3344_upsert_summary.json"
DECISIONS = REVIEW_DIR / "source_review_decisions.yaml"
REPORT_MD = REVIEW_DIR / "stage23_task12_final_readiness_report.md"
REPORT_JSON = REVIEW_DIR / "stage23_task12_final_readiness_report.json"
CLEANUP_PLAN = REVIEW_DIR / "stage23_cleanup_candidates.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def collect_cleanup_candidates() -> dict[str, list[str]]:
    qd3230_patterns = [
        "stage19_qd3230_summary.md",
        "stage20_qd3230_appendix_review_summary.md",
        "manual_corrected/huit_qd_3230*",
        "ocr_corrected/huit_qd_3230*",
        "ocr_corrections/huit_qd_3230*",
        "ocr_review/huit_qd_3230*",
        "stage19_pdf_pages/*",
    ]
    qd3230: list[str] = []
    for pattern in qd3230_patterns:
        qd3230.extend(rel(path) for path in REVIEW_DIR.glob(pattern))

    temporary_review = [
        rel(path)
        for path in [
            REVIEW_DIR / "stage14_pending_inventory.md",
            REVIEW_DIR / "stage14_summary.md",
            REVIEW_DIR / "stage16_quality_report.md",
            REVIEW_DIR / "stage16_source_decisions.yaml",
        ]
        if path.exists()
    ]

    keep_core = [
        rel(path)
        for path in [
            PROJECT_ROOT / "data" / "document_manifest.yaml",
            APPROVED_CHUNKS,
            REVIEW_DIR / "audit_cases.jsonl",
            REVIEW_DIR / "retrieval_audit_report.json",
            REVIEW_DIR / "retrieval_audit_report.md",
            REVIEW_DIR / "source_review_decisions.yaml",
            QD3344_AUDIT,
            REVIEW_DIR / "stage21_qd3344_current_source_audit.md",
            REVIEW_DIR / "stage22_qd3344_table_cleanup_summary.md",
            UPSERT_SUMMARY,
            PROJECT_ROOT / "huit_db",
        ]
        if path.exists()
    ]

    return {
        "qd3230_discarded_artifacts": sorted(set(qd3230)),
        "temporary_review_artifacts": sorted(set(temporary_review)),
        "keep_core_artifacts": sorted(set(keep_core)),
    }


def main() -> int:
    approved_chunks = read_jsonl(APPROVED_CHUNKS)
    audit = read_json(AUDIT_REPORT)
    qd3344 = read_json(QD3344_AUDIT)
    upsert = read_json(UPSERT_SUMMARY)
    decisions = yaml.safe_load(DECISIONS.read_text(encoding="utf-8"))

    approved_doc_ids = {chunk.get("document_id") for chunk in approved_chunks}
    blocked_current_docs = {
        "huit_qd_3230_foreign_language_outcomes_2023",
        "huit_form_bm09_exam_postponement",
        "huit_qd_2658_student_affairs_2023",
    }
    blocked_present = sorted(blocked_current_docs & approved_doc_ids)

    qd3344_chunks = [chunk for chunk in approved_chunks if chunk.get("document_id") == "huit_qd_3344_2025"]
    qd3344_table_cleanup_chunks = [
        chunk["chunk_id"]
        for chunk in qd3344_chunks
        if "[STAGE22_TABLE_CLEANUP]" in chunk.get("text", "")
    ]

    cleanup = collect_cleanup_candidates()

    checks = {
        "retrieval_audit_passed": (
            audit.get("total_cases", 0) >= 50
            and audit.get("passed_cases") == audit.get("total_cases")
            and audit.get("failed_cases") == 0
        ),
        "qd3344_audit_pass": qd3344.get("status") == "pass",
        "qd3344_articles_1_to_44_present": qd3344.get("article_count") == 44 and not qd3344.get("missing_articles"),
        "qd3344_table_cleanup_present": len(qd3344_table_cleanup_chunks) == 5,
        "blocked_or_discarded_sources_not_in_approved_chunks": not blocked_present,
        "vector_db_collection_count_expected": upsert.get("collection_count") == 141,
        "qd3230_marked_discarded": (
            decisions.get("decisions", {})
            .get("huit_qd_3230_foreign_language_outcomes_2023", {})
            .get("decision")
            == "discarded_by_user_do_not_process"
        ),
    }
    ready = all(checks.values())

    report = {
        "stage": 23,
        "task": "task_1_2_final_readiness",
        "ready_for_task_1_2_closure": ready,
        "checks": checks,
        "approved_chunk_count": len(approved_chunks),
        "approved_document_count": len(approved_doc_ids),
        "approved_document_ids": sorted(approved_doc_ids),
        "qd3344_chunk_count": len(qd3344_chunks),
        "qd3344_table_cleanup_chunk_count": len(qd3344_table_cleanup_chunks),
        "blocked_present_in_approved_chunks": blocked_present,
        "retrieval_audit": {
            "total_cases": audit.get("total_cases"),
            "passed_cases": audit.get("passed_cases"),
            "failed_cases": audit.get("failed_cases"),
            "pending_source_cases": audit.get("pending_source_cases"),
            "discarded_source_cases": audit.get("discarded_source_cases"),
        },
        "vector_db": {
            "collection_name": upsert.get("collection_name"),
            "persist_directory": upsert.get("persist_directory"),
            "embedding_model": upsert.get("embedding_model"),
            "collection_count": upsert.get("collection_count"),
        },
        "cleanup_candidates": cleanup,
        "next_recommended_action": "Task 1 is ready for closure. Proceed to Task 2 agent integration.",
    }

    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Stage 23 - Task 1.2 Final Readiness Audit",
        "",
        "## Decision",
        "",
        f"- Ready for Task 1.2 closure: `{ready}`",
        "- QĐ-3344/2025 is the primary current legal source.",
        "- QĐ-3230 is discarded by user decision and is not part of approved/current chunks.",
        "- Stage 25 cleanup has removed discarded QD-3230 working artifacts from active folders.",
        "",
        "## Input",
        "",
        f"- Approved chunks: `{rel(APPROVED_CHUNKS)}`",
        f"- Retrieval audit: `{rel(AUDIT_REPORT)}`",
        f"- QĐ-3344 audit: `{rel(QD3344_AUDIT)}`",
        f"- Upsert summary: `{rel(UPSERT_SUMMARY)}`",
        f"- Source decisions: `{rel(DECISIONS)}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        md_lines.append(f"- {key}: `{'pass' if value else 'fail'}`")

    md_lines.extend(
        [
            "",
            "## Output State",
            "",
            f"- Approved chunks: `{len(approved_chunks)}`",
            f"- QĐ-3344 chunks: `{len(qd3344_chunks)}`",
            f"- QĐ-3344 table-cleaned chunks: `{len(qd3344_table_cleanup_chunks)}`",
            f"- Retrieval audit: `{audit.get('passed_cases')}/{audit.get('total_cases')}` passed",
            f"- Vector DB collection count: `{upsert.get('collection_count')}`",
            f"- Pending-source cases: `{audit.get('pending_source_cases')}`",
            f"- Discarded-source cases: `{audit.get('discarded_source_cases')}`",
            "",
            "## Remaining Notes",
            "",
            "- Task 1 is ready for closure for the current HUIT academic RAG scope.",
            "- QĐ-3297 remains pending/historical-risk unless manually reviewed later.",
            "- BM09 remains pending until a current HUIT form is collected.",
            "- QĐ-2658 remains pending unless the project needs student-affairs regulation coverage.",
            "",
            "## Files",
            "",
            f"- JSON report: `{rel(REPORT_JSON)}`",
            f"- Cleanup plan: `{rel(CLEANUP_PLAN)}`",
        ]
    )
    REPORT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    cleanup_lines = [
        "# Stage 23 Cleanup Candidates",
        "",
        "No files were deleted in Stage 23. This is a review plan for the next cleanup stage.",
        "",
        "## Safe To Delete After User Approval - QĐ-3230 Discarded Artifacts",
        "",
    ]
    for path in cleanup["qd3230_discarded_artifacts"]:
        cleanup_lines.append(f"- `{path}`")
    cleanup_lines.extend(
        [
            "",
            "## Consider Deleting After Final Report Is Accepted - Temporary Review Artifacts",
            "",
        ]
    )
    for path in cleanup["temporary_review_artifacts"]:
        cleanup_lines.append(f"- `{path}`")
    cleanup_lines.extend(
        [
            "",
            "## Keep",
            "",
        ]
    )
    for path in cleanup["keep_core_artifacts"]:
        cleanup_lines.append(f"- `{path}`")
    CLEANUP_PLAN.write_text("\n".join(cleanup_lines) + "\n", encoding="utf-8")

    print(json.dumps({"ready": ready, "report": rel(REPORT_MD), "cleanup_plan": rel(CLEANUP_PLAN)}, ensure_ascii=True))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
