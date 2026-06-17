from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed_chunks_enriched.jsonl"
DECISIONS_PATH = PROJECT_ROOT / "data" / "review" / "source_review_decisions.yaml"
REPORT_PATH = PROJECT_ROOT / "data" / "review" / "stage21_qd3344_current_source_audit.md"
JSON_REPORT_PATH = PROJECT_ROOT / "data" / "review" / "stage21_qd3344_current_source_audit.json"

DOCUMENT_ID = "huit_qd_3344_2025"


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def find_article_number(chunk: dict) -> str | None:
    metadata = chunk.get("metadata") or {}
    article_number = metadata.get("article_number")
    if article_number:
        return str(article_number)
    match = re.search(r"Điều\s+(\d+)", chunk.get("text", ""))
    return match.group(1) if match else None


def citation_ok(citation: str) -> bool:
    return bool(
        re.search(
            r"Quyết định số 3344/QĐ-DCT ngày \d{2}/\d{2}/\d{4}, Điều \d+",
            citation,
        )
    )


def update_qd3230_decision() -> None:
    if not DECISIONS_PATH.exists():
        return
    data = yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8")) or {}
    decisions = data.setdefault("decisions", {})
    decision = decisions.setdefault("huit_qd_3230_foreign_language_outcomes_2023", {})
    decision.update(
        {
            "decision": "discarded_by_user_do_not_process",
            "can_vectorize": False,
            "can_use_for_current_policy": False,
            "can_use_for_form_hint": False,
            "can_use_for_historical_comparison": False,
            "required_next_action": "Do not continue processing QD-3230. Keep only as temporary review artifact until final cleanup.",
            "warning_note": "User requested to drop QD-3230 and prioritize QD-3344/2025 as the applicable current regulation.",
        }
    )
    data["stage"] = 21
    DECISIONS_PATH.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def main() -> None:
    chunks = [row for row in read_jsonl(CHUNKS_PATH) if row.get("document_id") == DOCUMENT_ID]
    article_to_chunks: dict[str, list[dict]] = defaultdict(list)
    unit_counts = Counter()
    metadata_issues: list[str] = []
    citation_issues: list[str] = []
    table_notes: list[dict] = []

    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        unit_counts[chunk.get("unit_type", "unknown")] += 1
        article_number = find_article_number(chunk)
        if article_number:
            article_to_chunks[article_number].append(chunk)

        if metadata.get("source_type") != "regulation":
            metadata_issues.append(f"{chunk['chunk_id']}: source_type is not regulation")
        if metadata.get("priority_score") != 100:
            metadata_issues.append(f"{chunk['chunk_id']}: priority_score is not 100")
        if metadata.get("is_current") is not True:
            metadata_issues.append(f"{chunk['chunk_id']}: is_current is not true")
        if metadata.get("use_as_primary_legal_source") is not True:
            metadata_issues.append(f"{chunk['chunk_id']}: use_as_primary_legal_source is not true")

        citation = str(metadata.get("citation", ""))
        if not citation_ok(citation):
            citation_issues.append(f"{chunk['chunk_id']}: {citation}")

        text = chunk.get("text", "")
        has_table_caption = bool(re.search(r"Bảng\s+\d+\.", text))
        if has_table_caption:
            table_notes.append(
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "article": article_number,
                    "has_markdown_table": "|" in text,
                    "has_flattened_math_or_symbols": any(token in text for token in ["", "", "TCHPi"]),
                    "snippet": text[:220].replace("\n", " "),
                }
            )

    # The supplied PDF text layer contains the attached regulation from Article 1
    # through Article 44, followed by the attached-form index.
    expected_articles = {str(i) for i in range(1, 45)}
    present_articles = set(article_to_chunks)
    missing_articles = sorted(expected_articles - present_articles, key=int)

    critical_checks = {
        "article_18_training_time_table_present": any(
            "Bảng 1" in chunk.get("text", "") for chunk in article_to_chunks.get("18", [])
        ),
        "article_30_academic_warning_present": bool(article_to_chunks.get("30")),
        "article_34_exam_absence_or_postponement_present": bool(article_to_chunks.get("34")),
        "article_39_graduation_conditions_present": bool(article_to_chunks.get("39")),
        "article_40_five_percent_rule_present": any(
            "5%" in chunk.get("text", "") and "giảm đi một mức" in chunk.get("text", "")
            for chunk in article_to_chunks.get("40", [])
        ),
        "article_44_final_article_present": bool(article_to_chunks.get("44")),
    }

    status = "pass"
    if missing_articles or metadata_issues or citation_issues or not all(critical_checks.values()):
        status = "needs_fix"
    if any(not note["has_markdown_table"] or note["has_flattened_math_or_symbols"] for note in table_notes):
        status = "pass_with_table_review_recommended" if status == "pass" else status

    report = {
        "document_id": DOCUMENT_ID,
        "status": status,
        "chunk_count": len(chunks),
        "unit_counts": dict(unit_counts),
        "article_count": len(present_articles),
        "missing_articles": missing_articles,
        "metadata_issue_count": len(metadata_issues),
        "citation_issue_count": len(citation_issues),
        "critical_checks": critical_checks,
        "table_notes": table_notes,
        "recommendation": (
            "QD-3344 is suitable as the primary current legal source. "
            "Do a targeted table cleanup for table-heavy articles before final cleanup."
        ),
        "boundary_note": "The supplied PDF contains Articles 1-44 and the attached-form index; Articles 45-46 were not found in this file.",
    }

    JSON_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Stage 21 - QĐ-3344 Current Source Audit",
        "",
        "## Decision",
        "",
        f"- Status: `{status}`",
        "- QĐ-3344 remains the primary current legal source for HUIT academic-policy answers.",
        "- The supplied PDF contains Articles 1-44 and the attached-form index; Articles 45-46 were not found in this file.",
        "- QĐ-3230 was marked as discarded/do-not-process per user instruction.",
        "",
        "## Input",
        "",
        f"- Chunk source: `{CHUNKS_PATH.relative_to(PROJECT_ROOT)}`",
        f"- Review decision file: `{DECISIONS_PATH.relative_to(PROJECT_ROOT)}`",
        "",
        "## Output",
        "",
        f"- JSON audit: `{JSON_REPORT_PATH.relative_to(PROJECT_ROOT)}`",
        f"- Markdown audit: `{REPORT_PATH.relative_to(PROJECT_ROOT)}`",
        "",
        "## Coverage",
        "",
        f"- QĐ-3344 chunk count: {len(chunks)}",
        f"- Article count detected: {len(present_articles)}/46",
        f"- Unit types: {dict(unit_counts)}",
        f"- Missing articles: {missing_articles if missing_articles else 'none'}",
        "",
        "## Metadata And Citation",
        "",
        f"- Metadata issues: {len(metadata_issues)}",
        f"- Citation format issues: {len(citation_issues)}",
        "- Expected citation date format: `ngày dd/mm/yyyy`.",
        "",
        "## Critical Checks",
        "",
    ]
    for key, value in critical_checks.items():
        lines.append(f"- {key}: {'pass' if value else 'fail'}")

    lines.extend(
        [
            "",
            "## Table Review",
            "",
            f"- Table-bearing chunks detected: {len(table_notes)}",
        ]
    )
    flattened = [note for note in table_notes if note["has_flattened_math_or_symbols"]]
    lines.append(f"- Chunks with flattened symbols/math likely needing cleanup: {len(flattened)}")
    for note in table_notes:
        flag = "needs targeted cleanup" if note["has_flattened_math_or_symbols"] else "ok/acceptable"
        lines.append(f"- Article {note['article']}, `{note['chunk_id']}`: {flag}")

    lines.extend(
        [
            "",
            "## Recommended Next Stage",
            "",
            "Stage 22 should perform targeted cleanup for QĐ-3344 table-heavy chunks only, especially formulas and converted tables, then rerun retrieval audit.",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    update_qd3230_decision()
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
