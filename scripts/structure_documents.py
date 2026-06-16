from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "document_manifest.yaml"
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "processed_clean"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "intermediate" / "structured_documents.jsonl"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "intermediate" / "structure_summary.json"


CHAPTER_RE = re.compile(r"(?m)^Chương\s+([IVXLCDM]+)\s*(.*)$", re.IGNORECASE)
ARTICLE_RE = re.compile(r"(?m)^Điều\s+(\d+)\.\s*(.*)$")
CLAUSE_RE = re.compile(r"(?m)^(\d+)\.\s+(.+?)(?=^\d+\.\s+|^[a-zđ]\)\s+|^Điều\s+\d+\.|\Z)", re.DOTALL)
POINT_RE = re.compile(r"(?m)^([a-zđ])\)\s+(.+?)(?=^[a-zđ]\)\s+|^\d+\.\s+|^Điều\s+\d+\.|\Z)", re.DOTALL)
GUIDANCE_SECTION_RE = re.compile(r"(?m)^(\d+)\.\s+(.+)$")
STEP_RE = re.compile(r"(?m)^(Bước\s+\d+):?\s*(.*)$", re.IGNORECASE)


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


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_page_for_heading(clean_doc: dict[str, Any], heading: str) -> int | None:
    pages = clean_doc.get("pages") or []
    if not pages:
        return None
    heading_norm = compact(heading)
    for page in pages:
        page_text = compact(page.get("clean_text") or page.get("text") or "")
        if heading_norm and heading_norm in page_text:
            return page.get("page")
    return None


def line_starts(pattern: re.Pattern[str], text: str) -> list[re.Match[str]]:
    return list(pattern.finditer(text))


def slice_sections(matches: list[re.Match[str]], text: str) -> list[tuple[re.Match[str], str]]:
    sections: list[tuple[re.Match[str], str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match, text[start:end].strip()))
    return sections


def current_chapter_for(position: int, chapters: list[re.Match[str]]) -> dict[str, Any] | None:
    current: re.Match[str] | None = None
    for chapter in chapters:
        if chapter.start() <= position:
            current = chapter
        else:
            break
    if current is None:
        return None
    return {
        "chapter_number": current.group(1),
        "chapter_title": compact(current.group(2)),
        "heading": compact(current.group(0)),
    }


def parse_clauses(article_text: str) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []
    for match, clause_text in slice_sections(line_starts(CLAUSE_RE, article_text), article_text):
        body = clause_text.strip()
        points = [
            {
                "point_number": point_match.group(1),
                "text": compact(point_text),
                "content_hash": content_hash(point_text),
            }
            for point_match, point_text in slice_sections(line_starts(POINT_RE, body), body)
        ]
        clauses.append(
            {
                "clause_number": match.group(1),
                "text": compact(body),
                "points": points,
                "content_hash": content_hash(body),
            }
        )
    return clauses


def structure_legal(document: dict[str, Any], clean_doc: dict[str, Any]) -> dict[str, Any]:
    text = clean_doc.get("clean_text", "")
    chapters = line_starts(CHAPTER_RE, text)
    article_matches = line_starts(ARTICLE_RE, text)
    articles: list[dict[str, Any]] = []

    for match, article_text in slice_sections(article_matches, text):
        article_number = match.group(1)
        article_title = compact(match.group(2))
        heading = f"Điều {article_number}. {article_title}".strip()
        chapter = current_chapter_for(match.start(), chapters)
        page_start = find_page_for_heading(clean_doc, heading)
        articles.append(
            {
                "article_number": article_number,
                "article_title": article_title,
                "heading": heading,
                "chapter": chapter,
                "page_start": page_start,
                "text": article_text,
                "clauses": parse_clauses(article_text),
                "content_hash": content_hash(article_text),
            }
        )

    return {
        "structure_type": "legal_articles",
        "chapters": [
            {
                "chapter_number": match.group(1),
                "chapter_title": compact(match.group(2)),
                "heading": compact(match.group(0)),
                "page_start": find_page_for_heading(clean_doc, compact(match.group(0))),
            }
            for match in chapters
        ],
        "articles": articles,
        "stats": {
            "chapter_count": len(chapters),
            "article_count": len(articles),
            "clause_count": sum(len(article["clauses"]) for article in articles),
            "point_count": sum(
                len(clause["points"])
                for article in articles
                for clause in article["clauses"]
            ),
        },
    }


def parse_steps(section_text: str) -> list[dict[str, Any]]:
    matches = line_starts(STEP_RE, section_text)
    return [
        {
            "step_label": match.group(1),
            "step_title": compact(match.group(2)),
            "text": step_text.strip(),
            "content_hash": content_hash(step_text),
        }
        for match, step_text in slice_sections(matches, section_text)
    ]


def structure_guidance(document: dict[str, Any], clean_doc: dict[str, Any]) -> dict[str, Any]:
    text = clean_doc.get("clean_text", "")
    section_matches = line_starts(GUIDANCE_SECTION_RE, text)
    title = text[: section_matches[0].start()].strip() if section_matches else ""
    sections: list[dict[str, Any]] = []
    for match, section_text in slice_sections(section_matches, text):
        section_number = match.group(1)
        section_title = compact(match.group(2))
        heading = f"{section_number}. {section_title}"
        sections.append(
            {
                "section_number": section_number,
                "section_title": section_title,
                "heading": heading,
                "page_start": find_page_for_heading(clean_doc, heading),
                "text": section_text,
                "steps": parse_steps(section_text),
                "has_note": bool(re.search(r"(?mi)^Lưu ý:?", section_text)),
                "content_hash": content_hash(section_text),
            }
        )
    return {
        "structure_type": "guidance_steps",
        "document_heading": compact(title),
        "sections": sections,
        "stats": {
            "section_count": len(sections),
            "step_count": sum(len(section["steps"]) for section in sections),
            "note_section_count": sum(1 for section in sections if section["has_note"]),
        },
    }


def extract_form_fields(text: str) -> list[str]:
    fields: list[str] = []
    for label in re.findall(r"([A-ZÀ-Ỵa-zà-ỵ0-9 /().-]{2,45}):", text):
        normalized = compact(label)
        normalized = re.sub(r"^[.…\-\s]+", "", normalized)
        if len(normalized.split()) > 6:
            continue
        if normalized.lower().startswith(("kính đề nghị", "em cam kết")):
            continue
        if normalized and normalized not in fields:
            fields.append(normalized)
    return fields


def extract_notes(text: str) -> list[str]:
    marker = re.search(r"(?mi)^Ghi chú:?\s*$", text)
    if not marker:
        return []
    note_text = text[marker.end() :].strip()
    return [line.strip("- ").strip() for line in note_text.splitlines() if line.strip()]


def structure_form(document: dict[str, Any], clean_doc: dict[str, Any]) -> dict[str, Any]:
    text = clean_doc.get("clean_text", "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    form_title = lines[0] if lines else clean_doc.get("title")
    tables = clean_doc.get("tables", [])
    table_markdown = clean_doc.get("table_markdown", [])
    return {
        "structure_type": "form_docx",
        "form_code": document.get("form_code"),
        "form_title": form_title,
        "related_procedure": document.get("related_procedure"),
        "fields": extract_form_fields(text),
        "notes": extract_notes(text),
        "tables": [
            {
                "table_index": index + 1,
                "rows": rows,
                "markdown": table_markdown[index] if index < len(table_markdown) else "",
            }
            for index, rows in enumerate(tables)
        ],
        "stats": {
            "field_count": len(extract_form_fields(text)),
            "note_count": len(extract_notes(text)),
            "table_count": len(tables),
        },
    }


def structure_faq(document: dict[str, Any], clean_doc: dict[str, Any]) -> dict[str, Any]:
    records = clean_doc.get("records", [])
    faqs = [
        {
            "faq_id": record.get("id") or f"{document['document_id']}_{index + 1}",
            "line_number": record.get("_line_number"),
            "category": record.get("category"),
            "question": record.get("question"),
            "answer": record.get("answer"),
            "content_hash": content_hash(f"{record.get('question', '')}\n{record.get('answer', '')}"),
        }
        for index, record in enumerate(records)
    ]
    return {
        "structure_type": "faq_jsonl",
        "faqs": faqs,
        "stats": {
            "faq_count": len(faqs),
            "categories": sorted({faq.get("category") for faq in faqs if faq.get("category")}),
        },
    }


def structure_pending_ocr(document: dict[str, Any], clean_doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "structure_type": "pending_ocr",
        "ocr_required": True,
        "manual_review_required": True,
        "stats": {
            "structured_unit_count": 0,
        },
    }


def structure_document(document: dict[str, Any], input_dir: Path) -> dict[str, Any]:
    clean_doc = load_json(input_dir / f"{document['document_id']}.json")
    profile = document.get("parser_profile")
    status = clean_doc.get("status")

    if status == "pending_ocr":
        structure = structure_pending_ocr(document, clean_doc)
    elif profile == "legal_articles":
        structure = structure_legal(document, clean_doc)
    elif profile == "guidance_steps":
        structure = structure_guidance(document, clean_doc)
    elif profile == "form_docx":
        structure = structure_form(document, clean_doc)
    elif profile == "faq_jsonl":
        structure = structure_faq(document, clean_doc)
    else:
        structure = {
            "structure_type": "unsupported",
            "stats": {"structured_unit_count": 0},
        }

    return {
        "document_id": document["document_id"],
        "source_path": document.get("path"),
        "title": document.get("title"),
        "source_type": document.get("source_type"),
        "parser_profile": profile,
        "status": "structured" if status == "cleaned" else status,
        "priority": document.get("priority"),
        "priority_score": document.get("priority_score"),
        "is_current": document.get("is_current"),
        "superseded_risk": document.get("superseded_risk", False),
        "requires_manual_review": document.get("requires_manual_review", False),
        "warning_note": document.get("warning_note"),
        "structure": structure,
    }


def validate_critical_rules(records: list[dict[str, Any]], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    records_by_id = {record["document_id"]: record for record in records}
    for rule in manifest.get("critical_rules", []):
        doc = records_by_id.get(rule.get("document_id"))
        if not doc:
            issues.append({"rule_id": rule.get("rule_id"), "status": "missing_document"})
            continue
        text = json.dumps(doc.get("structure", {}), ensure_ascii=False)
        hint = str(rule.get("expected_location_hint", ""))
        if "5%" in rule.get("requirement", "") and "5%" not in text:
            issues.append(
                {
                    "rule_id": rule.get("rule_id"),
                    "status": "missing_required_5_percent_text",
                    "expected_location_hint": hint,
                }
            )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Structure cleaned HUIT documents for chunking.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    args = parser.parse_args()

    manifest = load_yaml(args.manifest)
    records = [structure_document(document, args.input_dir) for document in manifest.get("documents", [])]
    write_jsonl(args.output_path, records)

    status_counts = Counter(record["status"] for record in records)
    profile_counts = Counter(record["parser_profile"] for record in records)
    structure_counts = Counter(record["structure"]["structure_type"] for record in records)
    critical_issues = validate_critical_rules(records, manifest)
    summary = {
        "manifest": str(args.manifest.relative_to(PROJECT_ROOT)),
        "input_dir": str(args.input_dir.relative_to(PROJECT_ROOT)),
        "output_path": str(args.output_path.relative_to(PROJECT_ROOT)),
        "total_documents": len(records),
        "status_counts": dict(status_counts),
        "parser_profile_counts": dict(profile_counts),
        "structure_type_counts": dict(structure_counts),
        "critical_rule_issues": critical_issues,
        "documents": [
            {
                "document_id": record["document_id"],
                "status": record["status"],
                "structure_type": record["structure"]["structure_type"],
                "stats": record["structure"].get("stats", {}),
            }
            for record in records
        ],
    }
    write_json(args.summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not critical_issues else 2


if __name__ == "__main__":
    sys.exit(main())
