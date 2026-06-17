from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHUNKS_PATH = PROJECT_ROOT / "data" / "processed_chunks_enriched.jsonl"
DEFAULT_REVIEW_ITEMS_PATH = PROJECT_ROOT / "data" / "review" / "manual_review_items.jsonl"
DEFAULT_APPROVED_PATH = PROJECT_ROOT / "data" / "review" / "approved_chunks.jsonl"
DEFAULT_PENDING_PATH = PROJECT_ROOT / "data" / "review" / "pending_chunks.jsonl"
DEFAULT_BLOCKED_PATH = PROJECT_ROOT / "data" / "review" / "rejected_or_blocked_chunks.jsonl"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "review" / "review_summary.json"
DEFAULT_FORMS_PREVIEW_DIR = PROJECT_ROOT / "data" / "forms_preview"


BLOCKING_REVIEW_REASONS = {
    "pending_ocr",
    "manifest_requires_manual_review",
}


PENDING_REVIEW_REASONS = {
    "superseded_or_legacy_risk",
    "tables_require_structured_review",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def group_review_items(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item["document_id"]].append(item)
    return grouped


def has_form_preview(chunk: dict[str, Any], forms_preview_dir: Path) -> bool:
    form_code = chunk.get("metadata", {}).get("form_code")
    if not form_code:
        return False
    stem = str(form_code).lower()
    return (forms_preview_dir / f"{stem}.md").exists() and (forms_preview_dir / f"{stem}.html").exists()


def classify_chunk(
    chunk: dict[str, Any],
    review_by_doc: dict[str, list[dict[str, Any]]],
    forms_preview_dir: Path,
) -> tuple[str, list[str]]:
    metadata = chunk.get("metadata", {})
    document_id = chunk["document_id"]
    doc_review_items = review_by_doc.get(document_id, [])
    reasons = [item["reason"] for item in doc_review_items]

    if metadata.get("requires_manual_review"):
        return "pending", ["chunk_requires_manual_review"]

    if metadata.get("warning_note") or metadata.get("superseded_risk"):
        return "pending", ["chunk_has_warning_or_legacy_risk"]

    if any(reason in BLOCKING_REVIEW_REASONS for reason in reasons):
        return "blocked", sorted(set(reasons).intersection(BLOCKING_REVIEW_REASONS))

    if any(reason in PENDING_REVIEW_REASONS for reason in reasons):
        if metadata.get("source_type") == "form":
            if set(reasons).issubset({"tables_require_structured_review"}) and has_form_preview(chunk, forms_preview_dir):
                return "approved", []
            return "pending", sorted(set(reasons).intersection(PENDING_REVIEW_REASONS))

    return "approved", []


def blocked_source_documents(review_by_doc: dict[str, list[dict[str, Any]]], chunk_doc_ids: set[str]) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    for document_id, items in sorted(review_by_doc.items()):
        if document_id in chunk_doc_ids:
            continue
        reasons = sorted({item["reason"] for item in items})
        if any(reason in BLOCKING_REVIEW_REASONS for reason in reasons):
            blocked.append(
                {
                    "document_id": document_id,
                    "status": "blocked_before_chunking",
                    "reasons": reasons,
                    "suggested_action": "Run OCR and manual review, then rerun extraction/cleaning/structuring/chunking before vector upsert.",
                }
            )
    return blocked


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply review gate before vector upsert.")
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--review-items-path", type=Path, default=DEFAULT_REVIEW_ITEMS_PATH)
    parser.add_argument("--approved-path", type=Path, default=DEFAULT_APPROVED_PATH)
    parser.add_argument("--pending-path", type=Path, default=DEFAULT_PENDING_PATH)
    parser.add_argument("--blocked-path", type=Path, default=DEFAULT_BLOCKED_PATH)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--forms-preview-dir", type=Path, default=DEFAULT_FORMS_PREVIEW_DIR)
    args = parser.parse_args()

    chunks = load_jsonl(args.chunks_path)
    review_items = load_jsonl(args.review_items_path)
    review_by_doc = group_review_items(review_items)

    approved: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()

    for chunk in chunks:
        classification, reasons = classify_chunk(chunk, review_by_doc, args.forms_preview_dir)
        gate_record = {
            **chunk,
            "review_gate": {
                "status": classification,
                "reasons": reasons,
            },
        }
        classification_counts[classification] += 1
        reason_counts.update(reasons)
        if classification == "approved":
            approved.append(gate_record)
        elif classification == "pending":
            pending.append(gate_record)
        else:
            blocked.append(gate_record)

    chunk_doc_ids = {chunk["document_id"] for chunk in chunks}
    blocked_documents = blocked_source_documents(review_by_doc, chunk_doc_ids)
    for document in blocked_documents:
        reason_counts.update(document["reasons"])

    write_jsonl(args.approved_path, approved)
    write_jsonl(args.pending_path, pending)
    write_jsonl(args.blocked_path, blocked)

    summary = {
        "chunks_path": str(args.chunks_path.relative_to(PROJECT_ROOT)),
        "review_items_path": str(args.review_items_path.relative_to(PROJECT_ROOT)),
        "approved_path": str(args.approved_path.relative_to(PROJECT_ROOT)),
        "pending_path": str(args.pending_path.relative_to(PROJECT_ROOT)),
        "blocked_path": str(args.blocked_path.relative_to(PROJECT_ROOT)),
        "forms_preview_dir": str(args.forms_preview_dir.relative_to(PROJECT_ROOT)),
        "total_chunks": len(chunks),
        "approved_chunks": len(approved),
        "pending_chunks": len(pending),
        "blocked_chunks": len(blocked),
        "blocked_source_documents": blocked_documents,
        "classification_counts": dict(classification_counts),
        "reason_counts": dict(reason_counts),
        "approved_source_type_counts": dict(Counter(chunk["metadata"].get("source_type") for chunk in approved)),
        "pending_document_ids": sorted({chunk["document_id"] for chunk in pending}),
    }
    write_json(args.summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
