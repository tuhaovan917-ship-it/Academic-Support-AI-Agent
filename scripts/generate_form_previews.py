from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STRUCTURED_PATH = PROJECT_ROOT / "data" / "intermediate" / "structured_documents.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "forms_preview"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "review" / "form_review_summary.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "form"


def row_signal(row: list[str]) -> int:
    return sum(1 for cell in row if str(cell).strip())


def clean_table_rows(rows: list[list[str]]) -> list[list[str]]:
    if not rows:
        return []
    cleaned: list[list[str]] = []
    for index, row in enumerate(rows):
        normalized = [str(cell).strip() for cell in row]
        if index == 0:
            cleaned.append(normalized)
            continue
        if row_signal(normalized) <= 1:
            continue
        if all(cell in {"", "1", "2", "3", "4", "5"} for cell in normalized):
            continue
        cleaned.append(normalized)
    return cleaned


def table_to_markdown(rows: list[list[str]]) -> str:
    rows = clean_table_rows(rows)
    if not rows:
        return ""
    max_cols = max(len(row) for row in rows)
    normalized = [row + [""] * (max_cols - len(row)) for row in rows]
    lines = [
        "| " + " | ".join(normalized[0]) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def markdown_to_html(markdown: str, title: str) -> str:
    body_lines: list[str] = []
    in_list = False
    in_table = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            if in_list:
                body_lines.append("</ul>")
                in_list = False
            if in_table:
                body_lines.append("</table>")
                in_table = False
            continue
        if stripped.startswith("# "):
            body_lines.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            body_lines.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("- "):
            if not in_list:
                body_lines.append("<ul>")
                in_list = True
            body_lines.append(f"<li>{html.escape(stripped[2:])}</li>")
        elif stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(cell == "---" for cell in cells):
                continue
            if not in_table:
                body_lines.append("<table>")
                in_table = True
            tag = "th" if "<tr>" not in "".join(body_lines[-2:]) else "td"
            body_lines.append("<tr>" + "".join(f"<{tag}>{html.escape(cell)}</{tag}>" for cell in cells) + "</tr>")
        else:
            if in_list:
                body_lines.append("</ul>")
                in_list = False
            if in_table:
                body_lines.append("</table>")
                in_table = False
            body_lines.append(f"<p>{html.escape(stripped)}</p>")
    if in_list:
        body_lines.append("</ul>")
    if in_table:
        body_lines.append("</table>")

    return """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.5; max-width: 920px; margin: 32px auto; padding: 0 16px; color: #1f2937; }}
    h1 {{ font-size: 24px; margin-bottom: 8px; }}
    h2 {{ font-size: 18px; margin-top: 24px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    code {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
{body}
</body>
</html>
""".format(title=html.escape(title), body="\n".join(body_lines))


def build_markdown(record: dict[str, Any]) -> tuple[str, bool]:
    structure = record["structure"]
    form_code = structure.get("form_code") or record["document_id"]
    title = structure.get("form_title") or record.get("title") or form_code
    warning = record.get("warning_note")
    requires_manual_review = bool(record.get("requires_manual_review"))
    approved_for_vector = not requires_manual_review and not warning

    lines = [
        f"# {form_code} - {title}",
        "",
        f"- Tệp gốc: `{record.get('source_path')}`",
        f"- Thủ tục liên quan: `{structure.get('related_procedure') or ''}`",
        f"- Trạng thái review: `{'approved_for_vector' if approved_for_vector else 'pending_review'}`",
    ]
    if warning:
        lines.append(f"- Cảnh báo: {warning}")

    if structure.get("fields"):
        lines.extend(["", "## Thông Tin Cần Điền"])
        lines.extend(f"- {field}" for field in structure["fields"])

    if structure.get("notes"):
        lines.extend(["", "## Ghi Chú Quan Trọng"])
        lines.extend(f"- {note}" for note in structure["notes"])

    tables_added = 0
    for table in structure.get("tables", []):
        markdown = table_to_markdown(table.get("rows", []))
        if not markdown:
            continue
        tables_added += 1
        lines.extend(["", f"## Bảng {tables_added}", markdown])

    return "\n".join(lines).strip() + "\n", approved_for_vector


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Markdown/HTML previews for HUIT forms.")
    parser.add_argument("--structured-path", type=Path, default=DEFAULT_STRUCTURED_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    args = parser.parse_args()

    records = [record for record in load_jsonl(args.structured_path) if record.get("source_type") == "form"]
    summary_records: list[dict[str, Any]] = []
    for record in records:
        form = record["structure"]
        form_code = form.get("form_code") or record["document_id"]
        markdown, approved_for_vector = build_markdown(record)
        file_stem = slug(form_code)
        md_path = args.output_dir / f"{file_stem}.md"
        html_path = args.output_dir / f"{file_stem}.html"
        write_text(md_path, markdown)
        write_text(html_path, markdown_to_html(markdown, f"{form_code} - {form.get('form_title', '')}"))
        summary_records.append(
            {
                "document_id": record["document_id"],
                "form_code": form_code,
                "form_title": form.get("form_title"),
                "status": "approved_for_vector" if approved_for_vector else "pending_review",
                "warning_note": record.get("warning_note"),
                "markdown_path": str(md_path.relative_to(PROJECT_ROOT)),
                "html_path": str(html_path.relative_to(PROJECT_ROOT)),
                "field_count": len(form.get("fields", [])),
                "note_count": len(form.get("notes", [])),
                "table_count": len(form.get("tables", [])),
            }
        )

    summary = {
        "total_forms": len(summary_records),
        "approved_for_vector": sum(1 for record in summary_records if record["status"] == "approved_for_vector"),
        "pending_review": sum(1 for record in summary_records if record["status"] == "pending_review"),
        "forms": summary_records,
    }
    write_json(args.summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
