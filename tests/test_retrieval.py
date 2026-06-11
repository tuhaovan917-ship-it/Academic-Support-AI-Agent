from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.retriever import load_vector_db


DEFAULT_QUERY = "Việc đánh giá điểm rèn luyện dựa trên bao nhiêu tiêu chí?"


def run_retrieval_test(query: str = DEFAULT_QUERY, k: int = 5) -> None:
    vector_db = load_vector_db()
    results = vector_db.similarity_search(query, k=k)

    print(f"Câu hỏi: {query}\n")
    print("--- Kết quả tìm thấy trong Database ---")
    for index, document in enumerate(results, start=1):
        source = document.metadata.get("source_name") or Path(
            document.metadata.get("source", "")
        ).name
        page = document.metadata.get("page_number")
        page_text = f", page={page}" if page else ""
        print(f"\nĐoạn {index} ({source}{page_text}):")
        print(document.page_content[:1000])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test retrieval từ Chroma DB.")
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="Câu hỏi dùng để test retrieval.",
    )
    parser.add_argument("--k", type=int, default=5, help="Số đoạn cần lấy ra.")
    args = parser.parse_args()
    run_retrieval_test(query=args.query, k=args.k)
