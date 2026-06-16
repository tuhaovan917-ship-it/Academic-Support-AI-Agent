from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "document_manifest.yaml"
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "processed_raw"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed_clean"
DEFAULT_REVIEW_PATH = PROJECT_ROOT / "data" / "review" / "manual_review_items.jsonl"


PAGE_NUMBER_RE = re.compile(r"^\s*\d+\s*$")
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
SOFT_LINEBREAK_PREFIX_RE = re.compile(
    r"^\s*(Điều\s+\d+\.|Chương\s+[IVXLCDM]+|PHẦN\s+\w+|\d+\.\s+|Bước\s+\d+|Lưu ý:?|Ghi chú:?)",
    re.IGNORECASE,
)


@dataclass
class CleanResult:
    document_id: str
    status: str
    output_path: str
    clean_text_chars: int
    review_items: int
    notes: list[str]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def normalize_symbols(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "–": "-",
        "−": "-",
        "➢": "-",
        "→": "->",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def looks_like_heading_or_list(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    if SOFT_LINEBREAK_PREFIX_RE.search(line):
        return True
    return line.startswith(("-", "+", "*"))


def should_join(previous: str, current: str) -> bool:
    previous = previous.rstrip()
    current = current.strip()
    if not previous or not current:
        return False
    if looks_like_heading_or_list(previous):
        return False
    if looks_like_heading_or_list(current):
        return False
    if previous.endswith((".", ":", ";", "!", "?", ")", "]")):
        return False
    if "|" in previous or "|" in current:
        return False
    return True


def clean_text(text: str) -> str:
    text = normalize_symbols(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [MULTISPACE_RE.sub(" ", line).strip() for line in text.split("\n")]

    cleaned_lines: list[str] = []
    for line in lines:
        if PAGE_NUMBER_RE.match(line):
            continue
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        if cleaned_lines and should_join(cleaned_lines[-1], line):
            cleaned_lines[-1] = f"{cleaned_lines[-1]} {line}"
        else:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    max_cols = max(len(row) for row in rows)
    normalized = [row + [""] * (max_cols - len(row)) for row in rows]
    header = normalized[0]
    separator = ["---"] * max_cols
    body = normalized[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def clean_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **page,
            "clean_text": clean_text(str(page.get("text", ""))),
        }
        for page in pages
    ]


def build_review_item(
    document: dict[str, Any],
    reason: str,
    severity: str = "medium",
    evidence: str | None = None,
    suggested_action: str | None = None,
) -> dict[str, Any]:
    item = {
        "document_id": document["document_id"],
        "title": document.get("title"),
        "source_path": document.get("path"),
        "source_type": document.get("source_type"),
        "parser_profile": document.get("parser_profile"),
        "reason": reason,
        "severity": severity,
    }
    if evidence:
        item["evidence"] = evidence[:500]
    if suggested_action:
        item["suggested_action"] = suggested_action
    return item


def detect_structure_issues(document: dict[str, Any], clean: dict[str, Any]) -> list[dict[str, Any]]:
    review_items: list[dict[str, Any]] = []
    text = clean.get("clean_text", "")
    profile = document.get("parser_profile")

    if clean.get("status") == "pending_ocr":
        review_items.append(
            build_review_item(
                document,
                "pending_ocr",
                "high",
                suggested_action="Run OCR, manually verify Vietnamese text and legal structure, then approve before vector upsert.",
            )
        )

    if document.get("requires_manual_review"):
        review_items.append(
            build_review_item(
                document,
                "manifest_requires_manual_review",
                "high" if document.get("requires_ocr") else "medium",
                evidence=document.get("warning_note") or document.get("extraction_notes"),
                suggested_action="Review source status and extracted content before using it as current evidence.",
            )
        )

    if document.get("superseded_risk"):
        review_items.append(
            build_review_item(
                document,
                "superseded_or_legacy_risk",
                "medium",
                evidence=document.get("warning_note"),
                suggested_action="Keep retrievable for history/comparison, but warn users and deprioritize for current-policy answers.",
            )
        )

    if profile == "legal_articles" and text:
        article_count = len(re.findall(r"(?m)^Điều\s+\d+\.", text))
        if article_count == 0:
            review_items.append(
                build_review_item(
                    document,
                    "legal_structure_missing_articles",
                    "high",
                    evidence=text[:300],
                    suggested_action="Check extraction/cleaning before chunking because legal article markers were not detected.",
                )
            )

    if profile == "guidance_steps" and text:
        step_count = len(re.findall(r"(?mi)^Bước\s+\d+", text))
        section_count = len(re.findall(r"(?m)^\d+\.\s+", text))
        if step_count == 0 and section_count == 0:
            review_items.append(
                build_review_item(
                    document,
                    "guidance_structure_unclear",
                    "medium",
                    evidence=text[:300],
                    suggested_action="Check headings and process steps before chunking guidance.",
                )
            )

    table_count = clean.get("table_count", 0)
    if table_count:
        review_items.append(
            build_review_item(
                document,
                "tables_require_structured_review",
                "medium",
                evidence=f"table_count={table_count}",
                suggested_action="Confirm Markdown/JSON table shape before chunking, especially forms and score-related tables.",
            )
        )

    return review_items


def clean_document(document: dict[str, Any], input_dir: Path, output_dir: Path) -> tuple[CleanResult, list[dict[str, Any]]]:
    document_id = document["document_id"]
    raw_path = input_dir / f"{document_id}.json"
    raw = load_json(raw_path)
    status = raw.get("status", "unknown")
    notes = list(raw.get("notes", []))

    payload: dict[str, Any] = {
        "document_id": document_id,
        "source_path": raw.get("source_path"),
        "title": raw.get("title"),
        "source_type": raw.get("source_type"),
        "parser_profile": raw.get("parser_profile"),
        "manifest_metadata": raw.get("manifest_metadata", {}),
        "raw_status": status,
        "status": "cleaned" if status == "extracted" else status,
        "notes": notes,
    }

    if status == "pending_ocr":
        payload.update(
            {
                "clean_text": "",
                "pages": [],
                "blocks": [],
                "tables": [],
                "table_markdown": [],
                "table_count": 0,
            }
        )
    elif "records" in raw:
        records = raw.get("records", [])
        cleaned_records = []
        for record in records:
            cleaned_record = dict(record)
            if "question" in cleaned_record:
                cleaned_record["question"] = clean_text(str(cleaned_record["question"]))
            if "answer" in cleaned_record:
                cleaned_record["answer"] = clean_text(str(cleaned_record["answer"]))
            cleaned_records.append(cleaned_record)
        clean_text_value = clean_text(
            "\n\n".join(
                f"Q: {record.get('question', '')}\nA: {record.get('answer', '')}"
                for record in cleaned_records
            )
        )
        payload.update(
            {
                "clean_text": clean_text_value,
                "records": cleaned_records,
                "record_count": len(cleaned_records),
                "table_count": 0,
            }
        )
    else:
        clean_text_value = clean_text(str(raw.get("text", "")))
        pages = clean_pages(raw.get("pages", []))
        blocks = raw.get("blocks", [])
        cleaned_blocks = [
            {
                **block,
                "clean_text": clean_text(str(block.get("text", ""))),
            }
            for block in blocks
        ]
        tables = raw.get("tables", [])
        table_markdown = [table_to_markdown(table) for table in tables]
        payload.update(
            {
                "clean_text": clean_text_value,
                "pages": pages,
                "blocks": cleaned_blocks,
                "tables": tables,
                "table_markdown": table_markdown,
                "table_count": len(tables),
            }
        )

    output_path = output_dir / f"{document_id}.json"
    write_json(output_path, payload)
    review_items = detect_structure_issues(document, payload)
    result = CleanResult(
        document_id=document_id,
        status=payload["status"],
        output_path=str(output_path),
        clean_text_chars=len(payload.get("clean_text", "")),
        review_items=len(review_items),
        notes=notes,
    )
    return result, review_items


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean raw extracted HUIT documents and build review queue.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--review-path", type=Path, default=DEFAULT_REVIEW_PATH)
    args = parser.parse_args()

    manifest = load_yaml(args.manifest)
    documents = manifest.get("documents", [])
    results: list[CleanResult] = []
    review_items: list[dict[str, Any]] = []

    for document in documents:
        result, items = clean_document(document, args.input_dir, args.output_dir)
        results.append(result)
        review_items.extend(items)

    status_counts = Counter(result.status for result in results)
    reason_counts = Counter(item["reason"] for item in review_items)
    summary = {
        "manifest": str(args.manifest.relative_to(PROJECT_ROOT)),
        "input_dir": str(args.input_dir.relative_to(PROJECT_ROOT)),
        "output_dir": str(args.output_dir.relative_to(PROJECT_ROOT)),
        "review_path": str(args.review_path.relative_to(PROJECT_ROOT)),
        "total_documents": len(results),
        "status_counts": dict(status_counts),
        "review_item_count": len(review_items),
        "review_reason_counts": dict(reason_counts),
        "documents": [result.__dict__ for result in results],
    }

    write_jsonl(args.review_path, review_items)
    write_json(args.output_dir / "_cleaning_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
