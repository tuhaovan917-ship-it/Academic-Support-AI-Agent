from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "document_manifest.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed_raw"


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass
class ExtractionResult:
    document_id: str
    status: str
    output_path: str | None
    text_chars: int
    page_count: int | None
    records_count: int | None
    notes: list[str]


def read_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def run_pdftotext(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    cmd = ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"]
    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    raw_pages = completed.stdout.split("\f")
    pages: list[dict[str, Any]] = []
    for index, page_text in enumerate(raw_pages, start=1):
        cleaned = normalize_text(page_text)
        if cleaned:
            pages.append({"page": index, "text": cleaned})
    notes: list[str] = []
    if not pages:
        notes.append("pdftotext returned no usable text")
    return pages, notes


def get_docx_paragraph_text(paragraph: ElementTree.Element) -> str:
    pieces: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{{{WORD_NS['w']}}}t" and node.text:
            pieces.append(node.text)
        elif node.tag == f"{{{WORD_NS['w']}}}tab":
            pieces.append(" ")
        elif node.tag == f"{{{WORD_NS['w']}}}br":
            pieces.append("\n")
    return normalize_text("".join(pieces))


def get_docx_table(table: ElementTree.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall("w:tr", WORD_NS):
        cells: list[str] = []
        for cell in row.findall("w:tc", WORD_NS):
            paragraphs = [
                get_docx_paragraph_text(paragraph)
                for paragraph in cell.findall(".//w:p", WORD_NS)
            ]
            cell_text = normalize_text(" ".join(p for p in paragraphs if p))
            cells.append(cell_text)
        if any(cells):
            rows.append(cells)
    return rows


def extract_docx(path: Path) -> tuple[list[dict[str, Any]], list[list[list[str]]], list[str]]:
    notes: list[str] = []
    with zipfile.ZipFile(path) as docx:
        with docx.open("word/document.xml") as f:
            root = ElementTree.fromstring(f.read())

    blocks: list[dict[str, Any]] = []
    tables: list[list[list[str]]] = []
    body = root.find("w:body", WORD_NS)
    if body is None:
        return blocks, tables, ["DOCX body not found"]

    block_index = 0
    for child in body:
        if child.tag == f"{{{WORD_NS['w']}}}p":
            text = get_docx_paragraph_text(child)
            if text:
                block_index += 1
                blocks.append({"block": block_index, "type": "paragraph", "text": text})
        elif child.tag == f"{{{WORD_NS['w']}}}tbl":
            table = get_docx_table(child)
            if table:
                tables.append(table)
                block_index += 1
                flattened = "\n".join(" | ".join(cell for cell in row) for row in table)
                blocks.append(
                    {
                        "block": block_index,
                        "type": "table",
                        "text": flattened,
                        "rows": table,
                    }
                )

    if tables:
        notes.append("DOCX tables extracted as raw rows; form preview/chunking must simplify blank fields later")
    return blocks, tables, notes


def extract_faq_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    notes: list[str] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                record["_line_number"] = line_number
                records.append(record)
            except json.JSONDecodeError as exc:
                notes.append(f"Invalid JSON at line {line_number}: {exc}")
    return records, notes


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def extract_document(doc: dict[str, Any], output_dir: Path) -> ExtractionResult:
    document_id = doc["document_id"]
    source_path = PROJECT_ROOT / doc["path"]
    output_path = output_dir / f"{document_id}.json"
    notes: list[str] = []

    base_payload: dict[str, Any] = {
        "document_id": document_id,
        "source_path": doc["path"],
        "title": doc.get("title"),
        "source_type": doc.get("source_type"),
        "parser_profile": doc.get("parser_profile"),
        "manifest_metadata": {
            key: value
            for key, value in doc.items()
            if key
            not in {
                "document_id",
                "path",
                "title",
                "source_type",
                "parser_profile",
            }
        },
    }

    if doc.get("requires_ocr"):
        payload = {
            **base_payload,
            "status": "pending_ocr",
            "text": "",
            "pages": [],
            "notes": [
                "Skipped raw text extraction because manifest requires OCR and manual review before vector upsert."
            ],
        }
        write_json(output_path, payload)
        return ExtractionResult(document_id, "pending_ocr", str(output_path), 0, 0, None, payload["notes"])

    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        pages, extraction_notes = run_pdftotext(source_path)
        notes.extend(extraction_notes)
        text = normalize_text("\n\n".join(page["text"] for page in pages))
        status = "extracted" if text else "needs_review"
        if not text:
            notes.append("Empty PDF text after extraction")
        payload = {
            **base_payload,
            "status": status,
            "text": text,
            "pages": pages,
            "notes": notes,
        }
        write_json(output_path, payload)
        return ExtractionResult(document_id, status, str(output_path), len(text), len(pages), None, notes)

    if suffix == ".docx":
        blocks, tables, extraction_notes = extract_docx(source_path)
        notes.extend(extraction_notes)
        text = normalize_text("\n\n".join(block["text"] for block in blocks))
        status = "extracted" if text else "needs_review"
        payload = {
            **base_payload,
            "status": status,
            "text": text,
            "blocks": blocks,
            "tables": tables,
            "notes": notes,
        }
        write_json(output_path, payload)
        return ExtractionResult(document_id, status, str(output_path), len(text), None, None, notes)

    if suffix == ".jsonl":
        records, extraction_notes = extract_faq_jsonl(source_path)
        notes.extend(extraction_notes)
        text = normalize_text(
            "\n\n".join(
                f"Q: {unescape(str(record.get('question', '')))}\nA: {unescape(str(record.get('answer', '')))}"
                for record in records
            )
        )
        status = "extracted" if records and not extraction_notes else "needs_review"
        payload = {
            **base_payload,
            "status": status,
            "text": text,
            "records": records,
            "notes": notes,
        }
        write_json(output_path, payload)
        return ExtractionResult(document_id, status, str(output_path), len(text), None, len(records), notes)

    payload = {
        **base_payload,
        "status": "unsupported",
        "text": "",
        "notes": [f"Unsupported file type: {suffix}"],
    }
    write_json(output_path, payload)
    return ExtractionResult(document_id, "unsupported", str(output_path), 0, None, None, payload["notes"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract raw text from HUIT manifest documents.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    manifest = read_manifest(args.manifest)
    documents = manifest.get("documents", [])
    results = [extract_document(doc, args.output_dir) for doc in documents]

    summary = {
        "manifest": str(args.manifest.relative_to(PROJECT_ROOT)),
        "output_dir": str(args.output_dir.relative_to(PROJECT_ROOT)),
        "total_documents": len(results),
        "status_counts": {},
        "documents": [result.__dict__ for result in results],
    }
    for result in results:
        summary["status_counts"][result.status] = summary["status_counts"].get(result.status, 0) + 1

    summary_path = args.output_dir / "_extraction_summary.json"
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
