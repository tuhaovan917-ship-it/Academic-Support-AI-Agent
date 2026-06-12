from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.retriever import hybrid_search, vector_search


DEFAULT_QUERY = "Việc đánh giá điểm rèn luyện dựa trên bao nhiêu tiêu chí?"


def run_retrieval_test(
    query: str = DEFAULT_QUERY,
    k: int = 5,
    vector_only: bool = False,
    school: str | None = None,
) -> None:
    search_fn = vector_search if vector_only else hybrid_search
    results = search_fn(query, k=k, school=school)
    search_mode = "Vector only" if vector_only else "Hybrid BM25 + Vector"

    print(f"Câu hỏi: {query}\n")
    print(f"Chế độ: {search_mode}")
    if school:
        print(f"Filter school: {school}")
    print("\n--- Kết quả tìm thấy trong Database ---")

    for index, document in enumerate(results, start=1):
        source = Path(document.metadata.get("source", "")).name
        school_value = document.metadata.get("school", "")
        category = document.metadata.get("category", "")
        hierarchy_path = document.metadata.get("hierarchy_path", "")
        section_heading = document.metadata.get("section_heading", "")
        chunk_type = document.metadata.get("chunk_type", "")

        print(f"\nĐoạn {index} ({source}, school={school_value}, category={category}, type={chunk_type}):")
        if section_heading:
            print(f"Section: {section_heading}")
        if hierarchy_path:
            print(f"Hierarchy: {hierarchy_path}")
        print(document.page_content[:1200])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test retrieval từ Chroma DB.")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Câu hỏi dùng để test retrieval.")
    parser.add_argument("--k", type=int, default=5, help="Số đoạn cần lấy ra.")
    parser.add_argument("--school", choices=["HCMUT", "NTTU"], help="Lọc kết quả theo trường.")
    parser.add_argument(
        "--vector-only",
        action="store_true",
        help="Chỉ dùng Chroma similarity_search, không dùng hybrid search.",
    )
    args = parser.parse_args()
    run_retrieval_test(
        query=args.query,
        k=args.k,
        vector_only=args.vector_only,
        school=args.school,
    )
