from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from src.data_processor import prepare_data
from src.retriever import setup_vector_db


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Chroma DB cho Task 1.2.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Xóa hcmut_nttu_db cũ trước khi tạo lại.",
    )
    parser.add_argument(
        "--force-markdown",
        action="store_true",
        help="Ép bóc tách PDF lại, bỏ qua file text đã cache trong data/processed.",
    )
    parser.add_argument(
        "--no-faq",
        action="store_true",
        help="Không đưa FAQ JSONL vào vector database.",
    )
    parser.add_argument(
        "--pdf",
        action="append",
        type=Path,
        help="Đường dẫn PDF cần xử lý. Có thể truyền nhiều lần. Mặc định: tất cả PDF trong data/.",
    )
    args = parser.parse_args()

    chunks = prepare_data(
        pdf_paths=args.pdf,
        force_markdown=args.force_markdown,
        include_faq=not args.no_faq,
    )
    setup_vector_db(chunks, reset=args.reset)
    print("Đã tạo/lưu Chroma DB vào thư mục hcmut_nttu_db.")


if __name__ == "__main__":
    main()
