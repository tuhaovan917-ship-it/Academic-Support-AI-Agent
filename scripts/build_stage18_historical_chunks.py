from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD = PROJECT_ROOT / "data" / "review" / "manual_corrected" / "huit_qd_3297_it_outcomes_2023.md"
SOURCE_META = PROJECT_ROOT / "data" / "review" / "manual_corrected" / "huit_qd_3297_it_outcomes_2023.meta.yaml"
OUTPUT_PATH = PROJECT_ROOT / "data" / "review" / "historical_warning_chunks.jsonl"
SUMMARY_PATH = PROJECT_ROOT / "data" / "review" / "stage18_historical_index_summary.md"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def split_manual_corrected(markdown: str) -> dict[str, str]:
    decision_match = re.search(r"## Quyết Định\n(?P<body>.*?)(?=\n## Quy Định Ban Hành Kèm Theo)", markdown, re.S)
    regulation_match = re.search(r"## Quy Định Ban Hành Kèm Theo\n(?P<body>.*?)(?=\n## Ghi Chú Rà Soát)", markdown, re.S)
    if not decision_match or not regulation_match:
        raise ValueError("Cannot locate QD-3297 decision/regulation sections in manual-corrected markdown.")

    regulation = regulation_match.group("body").strip()
    parts = {}
    article_matches = list(re.finditer(r"^### Điều (?P<number>\d+)\.?(?P<title>[^\n]*)\n", regulation, re.M))
    for index, match in enumerate(article_matches):
        start = match.start()
        end = article_matches[index + 1].start() if index + 1 < len(article_matches) else len(regulation)
        number = match.group("number")
        parts[f"regulation_article_{number}"] = regulation[start:end].strip()

    parts["decision"] = decision_match.group("body").strip()
    return parts


def build_chunk(
    document_id: str,
    unit_type: str,
    unit_key: str,
    text: str,
    base_metadata: dict[str, Any],
    article_number: str | None = None,
    article_title: str | None = None,
) -> dict[str, Any]:
    digest = content_hash(text)
    citation_bits = ["Quyết định số 3297/QĐ-DCT ngày 07/11/2023"]
    if article_number:
        citation_bits.append(f"Điều {article_number}")
    citation_bits.append("nguồn cảnh báo/lịch sử")
    metadata = {
        **base_metadata,
        "article_number": article_number or "",
        "article_title": article_title or "",
        "section_heading": f"Điều {article_number}. {article_title}" if article_number else "Quyết định",
        "content_hash": digest,
        "citation": ", ".join(citation_bits),
    }
    return {
        "chunk_id": f"{document_id}:{unit_type}:{unit_key}:{digest}",
        "document_id": document_id,
        "unit_type": unit_type,
        "unit_key": unit_key,
        "text": text,
        "metadata": metadata,
        "review_gate": {
            "status": "approved_with_warning",
            "reasons": ["stage18_historical_or_warning_source", "not_primary_current_policy"],
        },
    }


def main() -> int:
    meta = yaml.safe_load(SOURCE_META.read_text(encoding="utf-8"))
    markdown = SOURCE_MD.read_text(encoding="utf-8")
    sections = split_manual_corrected(markdown)

    document_id = meta["document_id"]
    warning = meta["warning_note"]
    base_metadata = {
        "document_id": document_id,
        "school": "HUIT",
        "source_path": meta["source_path"],
        "source_type": "historical_or_warning_source",
        "parser_profile": "manual_corrected_markdown",
        "document_title": meta["title"],
        "priority": "historical_warning",
        "priority_score": 30,
        "is_current": False,
        "superseded_risk": True,
        "requires_manual_review": False,
        "document_code": meta["document_code"],
        "decision_number": meta["decision_number"],
        "issued_date": meta["issued_date"],
        "display_issued_date": meta["display_issued_date"],
        "use_as_primary_legal_source": False,
        "warning_note": warning,
        "review_status": meta["review_status"],
        "historical_index_policy": "Indexed for historical/comparison or warning-backed CNTT output-standard questions; never primary current policy.",
    }

    chunks: list[dict[str, Any]] = [
        build_chunk(
            document_id=document_id,
            unit_type="historical_decision",
            unit_key="decision",
            text=sections["decision"],
            base_metadata=base_metadata,
        )
    ]
    article_titles = {
        "1": "Phạm vi điều chỉnh và đối tượng áp dụng",
        "2": "Chuẩn kỹ năng công nghệ thông tin",
        "3": "Tổ chức thực hiện",
        "4": "Điều khoản thi hành",
    }
    for key in ["regulation_article_1", "regulation_article_2", "regulation_article_3", "regulation_article_4"]:
        number = key.rsplit("_", 1)[1]
        chunks.append(
            build_chunk(
                document_id=document_id,
                unit_type="historical_regulation_article",
                unit_key=f"article_{number}",
                text=sections[key],
                base_metadata=base_metadata,
                article_number=number,
                article_title=article_titles[number],
            )
        )

    write_jsonl(OUTPUT_PATH, chunks)
    SUMMARY_PATH.write_text(
        "\n".join(
            [
                "# Stage 18 Historical/Warning Index Summary",
                "",
                "## Decision",
                "",
                "QD-3297 is prepared for vector indexing as `historical_or_warning_source`, not as a primary current-policy source.",
                "",
                "## Output",
                "",
                f"- Chunks: `{OUTPUT_PATH.relative_to(PROJECT_ROOT)}`",
                f"- Chunk count: `{len(chunks)}`",
                "",
                "## Policy",
                "",
                "- `is_current=false`",
                "- `use_as_primary_legal_source=false`",
                "- `superseded_risk=true`",
                "- `priority_score=30`",
                "- Answers using this source must include the warning note.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)} with {len(chunks)} chunks")
    print(f"Wrote {SUMMARY_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
