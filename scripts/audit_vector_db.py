from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.retriever import DEFAULT_CHROMA_DIR, load_documents_from_vector_db


def _filter_by_school(documents, school: str | None):
    if not school:
        return documents
    school = school.upper()
    return [doc for doc in documents if doc.metadata.get("school", "").upper() == school]


def audit_keyword(
    keyword: str = "rèn luyện",
    limit: int = 20,
    school: str | None = None,
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
) -> None:
    documents = _filter_by_school(load_documents_from_vector_db(persist_directory=persist_directory), school)
    keyword_lower = keyword.casefold()
    matched = [
        document
        for document in documents
        if keyword_lower in document.page_content.casefold()
    ]

    school_counts = Counter(doc.metadata.get("school", "UNKNOWN") for doc in documents)
    category_counts = Counter(doc.metadata.get("category", "khac") for doc in documents)
    toc_count = sum(
        1
        for doc in documents
        if doc.metadata.get("section_heading", "").casefold() == "mục lục"
    )
    too_long_count = sum(1 for doc in documents if len(doc.page_content) > 2600)

    print(f"Tổng số chunks trong DB: {len(documents)}")
    print(f"Chunks theo trường: {dict(school_counts)}")
    print(f"Top category: {dict(category_counts.most_common(12))}")
    print(f"Chunks thuộc MỤC LỤC: {toc_count}")
    print(f"Chunks dài hơn 2600 ký tự: {too_long_count}")
    print(f"Số chunks chứa từ khóa '{keyword}': {len(matched)}")

    if not matched:
        print(
            "\nKhông tìm thấy chunk nào. Khả năng cao bước bóc tách PDF, "
            "chunking hoặc nạp dữ liệu đã bỏ sót nội dung liên quan."
        )
        return

    print(f"\n--- Hiển thị tối đa {limit} chunks đầu tiên ---")
    for index, document in enumerate(matched[:limit], start=1):
        metadata = document.metadata
        print(f"\n[{index}]")
        print(f"source: {metadata.get('source', '')}")
        print(f"school: {metadata.get('school', '')}")
        print(f"category: {metadata.get('category', '')}")
        print(f"chunk_type: {metadata.get('chunk_type', '')}")
        print(f"section_heading: {metadata.get('section_heading', '')}")
        print(f"hierarchy_path: {metadata.get('hierarchy_path', '')}")
        print(document.page_content[:1200])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit nội dung trong Chroma DB.")
    parser.add_argument("--keyword", default="rèn luyện")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--school", choices=["HCMUT", "NTTU", "HUIT"])
    parser.add_argument("--persist-dir", type=Path, default=None)
    args = parser.parse_args()
    persist_dir = args.persist_dir
    if persist_dir is None and args.school == "HUIT":
        persist_dir = PROJECT_ROOT / "data" / "huit_db"
    audit_keyword(
        keyword=args.keyword,
        limit=args.limit,
        school=args.school,
        persist_directory=persist_dir or DEFAULT_CHROMA_DIR,
    )
