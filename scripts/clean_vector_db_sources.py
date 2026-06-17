from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_DIR = PROJECT_ROOT / "huit_db"
DEFAULT_COLLECTION = "huit_academic_chunks"
DEFAULT_REPORT_JSON = PROJECT_ROOT / "data" / "review" / "vector_db_cleanup_report.json"
DEFAULT_REPORT_MD = PROJECT_ROOT / "data" / "review" / "vector_db_cleanup_report.md"

DEFAULT_BLOCKED_DOCUMENT_IDS = [
    "huit_qd_3297_it_outcomes_2023",
    "huit_qd_3230_foreign_language_outcomes_2023",
    "huit_qd_2658_student_affairs_2023",
    "huit_form_bm09_exam_postponement",
]


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Vector DB Cleanup Report",
        "",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Persist directory: `{report['persist_directory']}`",
        f"- Collection: `{report['collection_name']}`",
        f"- Count before: `{report['count_before']}`",
        f"- Count after: `{report['count_after']}`",
        f"- Removed chunks: `{report['total_removed']}`",
        "",
        "## Removed by Document",
        "",
        "| document_id | matched_before | removed_ids |",
        "|---|---:|---:|",
    ]
    for item in report["removed_by_document"]:
        lines.append(
            f"| `{item['document_id']}` | `{item['matched_before']}` | `{len(item['removed_ids'])}` |"
        )
    lines.extend(
        [
            "",
            "## Remaining Blocked Documents",
            "",
            "| document_id | remaining_chunks |",
            "|---|---:|",
        ]
    )
    for item in report["remaining_blocked_documents"]:
        lines.append(f"| `{item['document_id']}` | `{item['remaining_chunks']}` |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clean_collection(
    db_dir: Path,
    collection_name: str,
    blocked_document_ids: list[str],
    dry_run: bool,
) -> dict[str, Any]:
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_collection(collection_name)
    count_before = collection.count()
    removed_by_document: list[dict[str, Any]] = []

    for document_id in blocked_document_ids:
        result = collection.get(where={"document_id": document_id})
        ids = list(result.get("ids", []))
        if ids and not dry_run:
            collection.delete(ids=ids)
        removed_by_document.append(
            {
                "document_id": document_id,
                "matched_before": len(ids),
                "removed_ids": ids,
            }
        )

    remaining_blocked_documents: list[dict[str, Any]] = []
    for document_id in blocked_document_ids:
        result = collection.get(where={"document_id": document_id})
        remaining_blocked_documents.append(
            {
                "document_id": document_id,
                "remaining_chunks": len(result.get("ids", [])),
            }
        )

    count_after = collection.count()
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "persist_directory": display_path(db_dir),
        "collection_name": collection_name,
        "blocked_document_ids": blocked_document_ids,
        "count_before": count_before,
        "count_after": count_after,
        "total_removed": sum(item["matched_before"] for item in removed_by_document) if not dry_run else 0,
        "removed_by_document": removed_by_document,
        "remaining_blocked_documents": remaining_blocked_documents,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove blocked or non-current HUIT sources from ChromaDB.")
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--document-id", action="append", dest="document_ids")
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    blocked_document_ids = args.document_ids or DEFAULT_BLOCKED_DOCUMENT_IDS
    report = clean_collection(
        db_dir=args.db_dir,
        collection_name=args.collection,
        blocked_document_ids=blocked_document_ids,
        dry_run=args.dry_run,
    )
    write_json(args.report_json, report)
    write_markdown(args.report_md, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
