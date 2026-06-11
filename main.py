from __future__ import annotations

import argparse
import sys

from src.data_processor import prepare_data
from src.retriever import setup_vector_db


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Chroma DB từ PDF và FAQ.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Xóa chroma_db cũ trước khi tạo lại để tránh dữ liệu trùng/lệch.",
    )
    parser.add_argument(
        "--no-faq",
        action="store_true",
        help="Chỉ index PDF, không đưa FAQ vào vector database.",
    )
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    args = parser.parse_args()

    chunks = prepare_data(
        include_faq=not args.no_faq,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    setup_vector_db(chunks, reset=args.reset)
    print("Đã tạo/lưu Chroma DB vào thư mục chroma_db.")


if __name__ == "__main__":
    main()
