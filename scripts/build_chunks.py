from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "document_manifest.yaml"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "intermediate" / "structured_documents.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed_chunks.jsonl"
DEFAULT_ENRICHED_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed_chunks_enriched.jsonl"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "intermediate" / "chunk_summary.json"

MAX_LEGAL_CHARS = 3200


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def stable_chunk_id(document_id: str, unit_type: str, unit_key: str, text: str) -> str:
    return f"{document_id}:{unit_type}:{unit_key}:{content_hash(text)}"


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def document_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {doc["document_id"]: doc for doc in manifest.get("documents", [])}


def base_metadata(record: dict[str, Any], manifest_doc: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "document_id": record["document_id"],
        "school": "HUIT",
        "source_path": record.get("source_path"),
        "source_type": record.get("source_type"),
        "parser_profile": record.get("parser_profile"),
        "document_title": record.get("title"),
        "priority": record.get("priority"),
        "priority_score": record.get("priority_score"),
        "is_current": record.get("is_current"),
        "superseded_risk": record.get("superseded_risk", False),
        "requires_manual_review": record.get("requires_manual_review", False),
        "warning_note": record.get("warning_note"),
        "document_code": manifest_doc.get("document_code"),
        "decision_number": manifest_doc.get("decision_number"),
        "issued_date": manifest_doc.get("issued_date"),
        "form_code": manifest_doc.get("form_code"),
        "related_procedure": manifest_doc.get("related_procedure"),
        "related_procedures": manifest_doc.get("related_procedures"),
        "related_forms": manifest_doc.get("related_forms"),
        "use_as_primary_legal_source": manifest_doc.get("use_as_primary_legal_source", True),
    }
    return {key: value for key, value in metadata.items() if value is not None}


def build_citation(metadata: dict[str, Any]) -> str:
    parts: list[str] = []
    if metadata.get("decision_number"):
        issued_date = format_vietnamese_date(str(metadata["issued_date"])) if metadata.get("issued_date") else ""
        issued = f" ngày {issued_date}" if issued_date else ""
        parts.append(f"Quyết định số {metadata['decision_number']}{issued}")
    elif metadata.get("document_title"):
        parts.append(str(metadata["document_title"]))

    if metadata.get("article_number"):
        article = f"Điều {metadata['article_number']}"
        if metadata.get("clause_number"):
            article += f", Khoản {metadata['clause_number']}"
        if metadata.get("point_number"):
            article += f", Điểm {metadata['point_number']}"
        parts.append(article)
    elif metadata.get("section_number"):
        parts.append(f"Mục {metadata['section_number']}: {metadata.get('section_heading', '')}".strip())
    elif metadata.get("form_code"):
        parts.append(f"Biểu mẫu {metadata['form_code']}")

    if metadata.get("page_start"):
        parts.append(f"trang {metadata['page_start']}")
    return ", ".join(part for part in parts if part)


def format_vietnamese_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value


def make_chunk(
    record: dict[str, Any],
    manifest_doc: dict[str, Any],
    unit_type: str,
    unit_key: str,
    text: str,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = base_metadata(record, manifest_doc)
    if extra_metadata:
        metadata.update({key: value for key, value in extra_metadata.items() if value is not None})
    metadata["content_hash"] = content_hash(text)
    metadata["citation"] = build_citation(metadata)
    chunk_id = stable_chunk_id(record["document_id"], unit_type, unit_key, text)
    return {
        "chunk_id": chunk_id,
        "document_id": record["document_id"],
        "unit_type": unit_type,
        "unit_key": unit_key,
        "text": text.strip(),
        "metadata": metadata,
    }


def build_legal_chunks(record: dict[str, Any], manifest_doc: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for article in record["structure"].get("articles", []):
        chapter = article.get("chapter") or {}
        article_metadata = {
            "chapter_number": chapter.get("chapter_number"),
            "chapter_title": chapter.get("chapter_title"),
            "article_number": article.get("article_number"),
            "article_title": article.get("article_title"),
            "section_heading": article.get("heading"),
            "page_start": article.get("page_start"),
        }
        article_text = article.get("text", "")
        if len(article_text) <= MAX_LEGAL_CHARS or not article.get("clauses"):
            chunks.append(
                make_chunk(
                    record,
                    manifest_doc,
                    "legal_article",
                    f"article_{article['article_number']}",
                    article_text,
                    article_metadata,
                )
            )
            continue

        for clause in article.get("clauses", []):
            clause_text = f"{article['heading']}\n{clause['text']}"
            clause_metadata = {
                **article_metadata,
                "clause_number": clause.get("clause_number"),
            }
            chunks.append(
                make_chunk(
                    record,
                    manifest_doc,
                    "legal_clause",
                    f"article_{article['article_number']}_clause_{clause['clause_number']}",
                    clause_text,
                    clause_metadata,
                )
            )
    return chunks


def build_guidance_chunks(record: dict[str, Any], manifest_doc: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    document_heading = record["structure"].get("document_heading")
    for section in record["structure"].get("sections", []):
        metadata = {
            "document_heading": document_heading,
            "section_number": section.get("section_number"),
            "section_heading": section.get("section_title"),
            "page_start": section.get("page_start"),
            "has_note": section.get("has_note"),
        }
        chunks.append(
            make_chunk(
                record,
                manifest_doc,
                "guidance_section",
                f"section_{section['section_number']}",
                section.get("text", ""),
                metadata,
            )
        )
    return chunks


def build_form_text(form: dict[str, Any]) -> str:
    lines = [form.get("form_title", "").strip()]
    if form.get("related_procedure"):
        lines.append(f"Thủ tục liên quan: {form['related_procedure']}")
    if form.get("fields"):
        lines.append("Các trường/thông tin cần điền:")
        lines.extend(f"- {field}" for field in form["fields"])
    if form.get("notes"):
        lines.append("Ghi chú quan trọng:")
        lines.extend(f"- {note}" for note in form["notes"])
    for table in form.get("tables", []):
        markdown = table.get("markdown")
        if markdown:
            lines.append(f"Bảng trong biểu mẫu {table['table_index']}:")
            lines.append(markdown)
    return "\n".join(line for line in lines if line).strip()


def build_form_chunks(record: dict[str, Any], manifest_doc: dict[str, Any]) -> list[dict[str, Any]]:
    form = record["structure"]
    text = build_form_text(form)
    metadata = {
        "form_code": form.get("form_code"),
        "form_name": form.get("form_title"),
        "related_procedure": form.get("related_procedure"),
        "field_count": form.get("stats", {}).get("field_count"),
        "note_count": form.get("stats", {}).get("note_count"),
        "table_count": form.get("stats", {}).get("table_count"),
        "downloadable": manifest_doc.get("downloadable"),
        "generate_preview": manifest_doc.get("generate_preview"),
    }
    return [
        make_chunk(
            record,
            manifest_doc,
            "form_summary",
            str(form.get("form_code") or record["document_id"]),
            text,
            metadata,
        )
    ]


def build_faq_chunks(record: dict[str, Any], manifest_doc: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for faq in record["structure"].get("faqs", []):
        text = f"Câu hỏi: {faq.get('question', '')}\nTrả lời: {faq.get('answer', '')}"
        metadata = {
            "faq_id": faq.get("faq_id"),
            "category": faq.get("category"),
            "line_number": faq.get("line_number"),
            "use_as_primary_legal_source": False,
        }
        chunks.append(
            make_chunk(
                record,
                manifest_doc,
                "faq",
                str(faq.get("faq_id")),
                text,
                metadata,
            )
        )
    return chunks


def build_chunks(records: list[dict[str, Any]], manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    docs = document_lookup(manifest)
    chunks: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for record in records:
        manifest_doc = docs[record["document_id"]]
        structure_type = record["structure"]["structure_type"]
        if record["status"] == "pending_ocr":
            skipped.append(
                {
                    "document_id": record["document_id"],
                    "reason": "pending_ocr_not_chunked",
                    "requires_manual_review": True,
                }
            )
            continue
        if structure_type == "legal_articles":
            chunks.extend(build_legal_chunks(record, manifest_doc))
        elif structure_type == "guidance_steps":
            chunks.extend(build_guidance_chunks(record, manifest_doc))
        elif structure_type == "form_docx":
            chunks.extend(build_form_chunks(record, manifest_doc))
        elif structure_type == "faq_jsonl":
            chunks.extend(build_faq_chunks(record, manifest_doc))
        else:
            skipped.append(
                {
                    "document_id": record["document_id"],
                    "reason": f"unsupported_structure_type:{structure_type}",
                }
            )
    return chunks, skipped


def validate_chunks(chunks: list[dict[str, Any]], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        if metadata.get("source_type") == "regulation" and not metadata.get("citation"):
            issues.append({"chunk_id": chunk["chunk_id"], "reason": "missing_regulation_citation"})

    critical_text = "\n".join(
        chunk["text"]
        for chunk in chunks
        if chunk["document_id"] == "huit_qd_3344_2025"
        and chunk["metadata"].get("article_number") == "40"
    )
    if "5%" not in critical_text:
        issues.append(
            {
                "rule_id": "graduation_classification_5_percent_retake",
                "reason": "article_40_chunks_missing_5_percent_rule",
            }
        )
    return issues


def public_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = chunk["metadata"]
    return {
        "chunk_id": chunk["chunk_id"],
        "text": chunk["text"],
        "metadata": metadata,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build chunk corpus from structured HUIT documents.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--enriched-output-path", type=Path, default=DEFAULT_ENRICHED_OUTPUT_PATH)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    args = parser.parse_args()

    manifest = load_yaml(args.manifest)
    records = load_jsonl(args.input_path)
    chunks, skipped = build_chunks(records, manifest)
    issues = validate_chunks(chunks, manifest)

    write_jsonl(args.output_path, [public_chunk(chunk) for chunk in chunks])
    write_jsonl(args.enriched_output_path, chunks)

    source_counts = Counter(chunk["metadata"].get("source_type") for chunk in chunks)
    unit_counts = Counter(chunk["unit_type"] for chunk in chunks)
    document_counts = Counter(chunk["document_id"] for chunk in chunks)
    review_needed_count = sum(1 for chunk in chunks if chunk["metadata"].get("requires_manual_review"))
    warning_count = sum(1 for chunk in chunks if chunk["metadata"].get("warning_note"))
    summary = {
        "manifest": str(args.manifest.relative_to(PROJECT_ROOT)),
        "input_path": str(args.input_path.relative_to(PROJECT_ROOT)),
        "output_path": str(args.output_path.relative_to(PROJECT_ROOT)),
        "enriched_output_path": str(args.enriched_output_path.relative_to(PROJECT_ROOT)),
        "total_chunks": len(chunks),
        "source_type_counts": dict(source_counts),
        "unit_type_counts": dict(unit_counts),
        "document_chunk_counts": dict(document_counts),
        "review_needed_chunk_count": review_needed_count,
        "warning_chunk_count": warning_count,
        "skipped_documents": skipped,
        "validation_issues": issues,
    }
    write_json(args.summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not issues else 2


if __name__ == "__main__":
    sys.exit(main())
