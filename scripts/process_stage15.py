from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "data" / "document_manifest.yaml"
OCR_DIR = PROJECT_ROOT / "data" / "processed_ocr"
OUTPUT_DIR = PROJECT_ROOT / "data" / "review" / "ocr_corrected"

DOC_IDS = [
    "huit_qd_3297_it_outcomes_2023",
    "huit_qd_3230_foreign_language_outcomes_2023",
    "huit_qd_2658_student_affairs_2023",
]

PRIORITY_ARTICLES_2658 = {"1", "2", "3", "4", "5", "6", "26", "27", "28", "29", "30", "31", "34"}


def normalize_text(value: str) -> str:
    text = value.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text.lower()).strip()


def load_manifest() -> dict[str, Any]:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def manifest_entry(manifest: dict[str, Any], doc_id: str) -> dict[str, Any]:
    for entry in manifest.get("documents", []):
        if entry.get("document_id") == doc_id:
            return entry
    raise KeyError(f"Document not found in manifest: {doc_id}")


def load_ocr(doc_id: str) -> dict[str, Any]:
    return json.loads((OCR_DIR / f"{doc_id}.json").read_text(encoding="utf-8"))


def clean_line(line: str) -> str:
    line = line.replace("\u00a0", " ")
    line = re.sub(r"[ \t]+", " ", line)
    return line.rstrip()


def article_match(line: str) -> re.Match[str] | None:
    stripped = clean_line(line).strip(" |._-")
    normalized = normalize_text(stripped)
    # OCR variants include Dieu, Diéu, Điều, and lines with minor punctuation noise.
    if not normalized.startswith("dieu "):
        return None
    return re.match(r"dieu\s+(\d+)\.?\s*(.*)$", normalized)


def extract_articles(text: str) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        match = article_match(line)
        if match:
            if current:
                articles.append(current)
            number = match.group(1)
            title = line.strip()
            current = {"number": number, "raw_title": title, "content": []}
            continue
        if current is not None:
            current["content"].append(line)

    if current:
        articles.append(current)
    return articles


def table_draft_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        cleaned = clean_line(line)
        if "|" in cleaned and len(cleaned.strip()) > 3:
            lines.append(cleaned)
    return lines


def render_article(article: dict[str, Any]) -> list[str]:
    lines = [
        f"### Điều {article['number']}. [NEEDS_PDF_VERIFICATION]",
        "",
        f"> OCR heading: {article['raw_title']}",
        "",
    ]
    content = [line for line in article["content"] if line.strip()]
    if content:
        lines.extend(content)
    else:
        lines.append("[UNVERIFIED: empty_or_unreadable_article_body]")
    lines.append("")
    return lines


def build_markdown(doc_id: str, entry: dict[str, Any], ocr: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    title = entry.get("title") or ocr.get("title") or doc_id
    manifest_decision = entry.get("decision_number")
    manifest_date = entry.get("issued_date")
    source_path = entry.get("path")

    articles = extract_articles(ocr.get("text", ""))
    pending_sections: list[str] = []
    if doc_id == "huit_qd_2658_student_affairs_2023":
        selected = [article for article in articles if article["number"] in PRIORITY_ARTICLES_2658]
        selected_numbers = {article["number"] for article in selected}
        pending_numbers = sorted({article["number"] for article in articles if article["number"] not in selected_numbers}, key=int)
        pending_sections = [f"Điều {number}" for number in pending_numbers]
    else:
        selected = articles

    generated_sections = [f"Điều {article['number']}" for article in selected]

    lines = [
        f"# [UNVERIFIED: Quyết định số {manifest_decision or 'decision_number'}]",
        "",
        "## Thông tin văn bản",
        "",
        "- Số quyết định: [UNVERIFIED: decision_number]",
        "- Ngày ban hành: [UNVERIFIED: issued_date]",
        "- Cơ quan ban hành: [NEEDS_PDF_VERIFICATION]",
        f"- Tên văn bản: {title}",
        f"- Đường dẫn nguồn: `{source_path}`",
        f"- Số quyết định theo manifest, chưa xác minh bằng PDF: `{manifest_decision}`",
        f"- Ngày ban hành theo manifest, chưa xác minh bằng PDF: `{manifest_date}`",
        "- Trạng thái xác minh: [NEEDS_PDF_VERIFICATION]",
        "",
        "## Ghi chú xử lý",
        "",
        "- Đây là bản nháp cấu trúc từ OCR, chưa phải văn bản đã hiệu đính pháp lý.",
        "- Không dùng bản này để trả lời quy định hiện hành hoặc đưa vào Vector DB.",
        "- Các tiêu đề Điều và nội dung bên dưới cần được đối chiếu lại với PDF gốc.",
        "",
        "## Nội dung OCR đã cấu trúc",
        "",
    ]

    if not selected:
        lines.extend(["[UNVERIFIED: no_article_heading_detected]", ""])
    for article in selected:
        lines.extend(render_article(article))

    if doc_id == "huit_qd_3230_foreign_language_outcomes_2023":
        drafts = table_draft_lines(ocr.get("text", ""))
        lines.extend(
            [
                "## Raw OCR Table Drafts",
                "",
                "[NEEDS_PDF_VERIFICATION]",
                "",
                "Các dòng dưới đây chỉ là nháp OCR có ký tự bảng; không được xem là bảng chuẩn.",
                "",
                "```text",
            ]
        )
        lines.extend(drafts or ["[UNVERIFIED: no_table_like_lines_detected]"])
        lines.extend(["```", ""])

    if doc_id == "huit_qd_2658_student_affairs_2023":
        lines.extend(
            [
                "## Phạm vi chưa xử lý",
                "",
                "[NEEDS_PDF_VERIFICATION]",
                "",
            ]
        )
        if pending_sections:
            lines.extend(f"- {section}" for section in pending_sections)
        else:
            lines.append("- Không phát hiện thêm Điều ngoài danh sách ưu tiên trong OCR parser.")
        lines.append("")

    return "\n".join(lines).strip() + "\n", generated_sections, pending_sections


def write_meta(
    doc_id: str,
    entry: dict[str, Any],
    generated_sections: list[str],
    pending_sections: list[str],
) -> None:
    meta: dict[str, Any] = {
        "document_id": doc_id,
        "source_path": entry.get("path"),
        "source_type": entry.get("source_type", "regulation"),
        "document_code": entry.get("document_code"),
        "decision_number": None,
        "issued_date": None,
        "manifest_expected_decision_number": entry.get("decision_number"),
        "manifest_expected_issued_date": entry.get("issued_date"),
        "title": entry.get("title"),
        "review_status": "draft_ocr_structured",
        "can_vectorize": False,
        "use_as_current_policy": False,
        "requires_final_human_check": True,
        "superseded_risk": bool(entry.get("superseded_risk", True)),
        "correction_source": "ocr_structuring_only",
        "verified_fields": [],
        "unverified_fields": [
            "decision_number",
            "issued_date",
            "issuing_authority",
            "article_titles",
            "article_content",
        ],
        "generated_sections": generated_sections,
        "review_notes": [
            "Structured from OCR only; not legally corrected.",
            "Decision number and issue date are intentionally left null until PDF visual verification.",
            "Do not vectorize until final Codex/user review and PDF verification.",
        ],
    }

    if doc_id == "huit_qd_3230_foreign_language_outcomes_2023":
        meta["unverified_fields"].append("foreign_language_threshold_tables")
        meta["review_notes"].append("Foreign-language tables are raw OCR drafts and must not be treated as verified thresholds.")

    if doc_id == "huit_qd_2658_student_affairs_2023":
        meta["corrected_sections"] = generated_sections
        meta["pending_sections"] = pending_sections or ["No additional article headings detected by OCR parser."]
        meta["review_notes"].append("Only priority student-affairs articles were included in this draft.")

    yaml_text = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
    (OUTPUT_DIR / f"{doc_id}.meta.yaml").write_text(yaml_text, encoding="utf-8")


def process_document(manifest: dict[str, Any], doc_id: str) -> None:
    entry = manifest_entry(manifest, doc_id)
    ocr = load_ocr(doc_id)
    markdown, generated_sections, pending_sections = build_markdown(doc_id, entry, ocr)
    (OUTPUT_DIR / f"{doc_id}.md").write_text(markdown, encoding="utf-8")
    write_meta(doc_id, entry, generated_sections, pending_sections)


def validate_outputs() -> None:
    for path in OUTPUT_DIR.glob("*"):
        if path.is_file():
            path.read_text(encoding="utf-8")
    for path in OUTPUT_DIR.glob("*.meta.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("can_vectorize") is not False:
            raise ValueError(f"can_vectorize must be false: {path}")
        if data.get("review_status") != "draft_ocr_structured":
            raise ValueError(f"review_status must be draft_ocr_structured: {path}")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    for doc_id in DOC_IDS:
        process_document(manifest, doc_id)
    validate_outputs()
    print("Stage 15 OCR structured drafts regenerated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
