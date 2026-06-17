from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "document_manifest.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed_ocr"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "data" / "review" / "ocr_review"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "review" / "ocr_summary.json"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def run_command(args: list[str], cwd: Path = PROJECT_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def render_pdf_pages(pdf_path: Path, output_prefix: Path, dpi: int) -> list[Path]:
    run_command(["pdftoppm", "-r", str(dpi), "-png", str(pdf_path), str(output_prefix)])
    return sorted(output_prefix.parent.glob(f"{output_prefix.name}-*.png"))


def ocr_image_text(image_path: Path, lang: str, psm: int) -> str:
    completed = run_command(["tesseract", str(image_path), "stdout", "-l", lang, "--psm", str(psm)])
    return normalize_text(completed.stdout)


def ocr_image_confidence(image_path: Path, lang: str, psm: int) -> dict[str, Any]:
    completed = run_command(["tesseract", str(image_path), "stdout", "-l", lang, "--psm", str(psm), "tsv"])
    confidences: list[float] = []
    for line in completed.stdout.splitlines()[1:]:
        cells = line.split("\t")
        if len(cells) < 12:
            continue
        text = cells[11].strip()
        if not text:
            continue
        try:
            conf = float(cells[10])
        except ValueError:
            continue
        if conf >= 0:
            confidences.append(conf)
    if not confidences:
        return {"word_count": 0, "avg_confidence": None, "low_confidence_ratio": None}
    low = sum(1 for value in confidences if value < 70)
    return {
        "word_count": len(confidences),
        "avg_confidence": round(sum(confidences) / len(confidences), 2),
        "low_confidence_ratio": round(low / len(confidences), 3),
    }


def quality_status(char_count: int, avg_confidence: float | None, low_confidence_ratio: float | None) -> str:
    if char_count < 500:
        return "needs_manual_review"
    if avg_confidence is None:
        return "needs_manual_review"
    if avg_confidence < 75 or (low_confidence_ratio is not None and low_confidence_ratio > 0.35):
        return "needs_manual_review"
    return "ocr_extracted_needs_review"


def build_review_markdown(document: dict[str, Any], payload: dict[str, Any]) -> str:
    lines = [
        f"# OCR Review - {document['document_id']}",
        "",
        f"- Tệp gốc: `{document['path']}`",
        f"- Tiêu đề: {document.get('title')}",
        f"- Trạng thái: `{payload['status']}`",
        f"- Số trang OCR: `{len(payload['pages'])}`",
        f"- Số ký tự: `{len(payload['text'])}`",
        f"- Confidence trung bình: `{payload['quality'].get('avg_confidence')}`",
        f"- Tỷ lệ từ confidence thấp: `{payload['quality'].get('low_confidence_ratio')}`",
        "",
        "## Việc Cần Review",
        "",
        "- Kiểm tra lỗi dấu tiếng Việt.",
        "- Kiểm tra nhận diện Điều/Khoản/Mục.",
        "- Kiểm tra tên quyết định, ngày ban hành, căn cứ pháp lý.",
        "- Chỉ approve vào Vector DB sau khi nội dung pháp lý đủ tin cậy.",
        "",
        "## Nội Dung OCR",
        "",
    ]
    for page in payload["pages"]:
        lines.extend([f"### Trang {page['page']}", "", page["text"], ""])
    return "\n".join(lines).strip() + "\n"


def ocr_document(document: dict[str, Any], output_dir: Path, review_dir: Path, dpi: int, lang: str, psm: int) -> dict[str, Any]:
    pdf_path = PROJECT_ROOT / document["path"]
    with tempfile.TemporaryDirectory(prefix=f"ocr_{document['document_id']}_") as temp:
        temp_dir = Path(temp)
        page_images = render_pdf_pages(pdf_path, temp_dir / "page", dpi)
        pages: list[dict[str, Any]] = []
        confidence_values: list[float] = []
        low_ratios: list[float] = []
        word_count = 0

        for index, image_path in enumerate(page_images, start=1):
            text = ocr_image_text(image_path, lang, psm)
            confidence = ocr_image_confidence(image_path, lang, psm)
            if confidence.get("avg_confidence") is not None:
                confidence_values.append(float(confidence["avg_confidence"]))
            if confidence.get("low_confidence_ratio") is not None:
                low_ratios.append(float(confidence["low_confidence_ratio"]))
            word_count += int(confidence.get("word_count") or 0)
            pages.append({"page": index, "text": text, "quality": confidence})

    full_text = normalize_text("\n\n".join(page["text"] for page in pages if page["text"]))
    avg_confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else None
    low_confidence_ratio = round(sum(low_ratios) / len(low_ratios), 3) if low_ratios else None
    status = quality_status(len(full_text), avg_confidence, low_confidence_ratio)
    payload = {
        "document_id": document["document_id"],
        "source_path": document["path"],
        "title": document.get("title"),
        "source_type": document.get("source_type"),
        "parser_profile": document.get("parser_profile"),
        "status": status,
        "ocr_engine": "tesseract",
        "ocr_lang": lang,
        "dpi": dpi,
        "psm": psm,
        "text": full_text,
        "pages": pages,
        "quality": {
            "char_count": len(full_text),
            "page_count": len(pages),
            "word_count": word_count,
            "avg_confidence": avg_confidence,
            "low_confidence_ratio": low_confidence_ratio,
        },
        "vector_upsert_allowed": False,
        "notes": [
            "OCR output requires manual review before this document can enter the vector database."
        ],
    }
    output_path = output_dir / f"{document['document_id']}.json"
    review_path = review_dir / f"{document['document_id']}.md"
    write_json(output_path, payload)
    write_text(review_path, build_review_markdown(document, payload))
    return {
        "document_id": document["document_id"],
        "status": status,
        "output_path": str(output_path.relative_to(PROJECT_ROOT)),
        "review_path": str(review_path.relative_to(PROJECT_ROOT)),
        "quality": payload["quality"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR scanned HUIT PDFs and create manual review files.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--lang", default="vie+eng")
    parser.add_argument("--psm", type=int, default=6)
    args = parser.parse_args()

    manifest = load_yaml(args.manifest)
    documents = [doc for doc in manifest.get("documents", []) if doc.get("requires_ocr")]
    results = [ocr_document(doc, args.output_dir, args.review_dir, args.dpi, args.lang, args.psm) for doc in documents]
    summary = {
        "total_documents": len(results),
        "vector_upsert_allowed": False,
        "reason": "All OCR outputs require manual review before vector upsert.",
        "documents": results,
    }
    write_json(args.summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
