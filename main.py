from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from src.data_processor import DATA_DIR, RAW_DIR, prepare_data
from src.retriever import DEFAULT_CHROMA_DIR, setup_vector_db


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
        help="Đường dẫn PDF/TXT cần xử lý. Có thể truyền nhiều lần.",
    )
    parser.add_argument(
        "--school",
        choices=["HCMUT", "NTTU", "HUIT"],
        help="Xử lý dữ liệu theo trường. Với HUIT sẽ đọc mặc định từ data/raw/HUIT.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Thư mục chứa PDF/TXT nguồn. Ghi đè mặc định theo --school.",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        help="Thư mục lưu Chroma DB. Mặc định: data/huit_db khi --school HUIT, còn lại hcmut_nttu_db.",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    if data_dir is None and args.school == "HUIT":
        data_dir = RAW_DIR / "HUIT"
    if data_dir is None:
        data_dir = DATA_DIR

    persist_dir = args.persist_dir
    if persist_dir is None and args.school == "HUIT":
        persist_dir = DATA_DIR / "huit_db"

    chunks = prepare_data(
        source_paths=args.pdf,
        data_dir=data_dir,
        force_markdown=args.force_markdown,
        include_faq=not args.no_faq,
    )
    persist_path = persist_dir or DEFAULT_CHROMA_DIR
    setup_vector_db(chunks, persist_directory=persist_path, reset=args.reset)
    print(f"Đã tạo/lưu Chroma DB vào thư mục {persist_path}.")


if __name__ == "__main__":
    main()
