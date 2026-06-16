from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.retriever import HUITAcademicRetriever


CASES = [
    (
        "Xếp loại tốt nghiệp có bị giảm nếu học lại quá 5% tín chỉ không?",
        "current_policy",
        "huit_qd_3344_2025",
        "40",
    ),
    (
        "Sinh viên muốn hủy học phần thì làm thế nào?",
        "procedure",
        "huit_guidance_course_registration_2026",
        None,
    ),
    (
        "Muốn xét tốt nghiệp thì dùng biểu mẫu nào?",
        "procedure",
        "huit_form_bm12_graduation_application",
        None,
    ),
    (
        "Thang điểm đánh giá kết quả học tập học phần tại HUIT như thế nào?",
        "current_policy",
        "huit_qd_3344_2025",
        "30",
    ),
]


def main() -> int:
    retriever = HUITAcademicRetriever()
    for query, intent, expected_document, expected_article in CASES:
        results = retriever.search(query, intent=intent, k=3)
        top = results[0]
        citation = top.metadata.get("citation")
        print(f"{query}\n -> {top.metadata.get('document_id')} | {citation}\n")
        assert top.metadata.get("document_id") == expected_document
        if expected_article:
            assert str(top.metadata.get("article_number")) == expected_article
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
