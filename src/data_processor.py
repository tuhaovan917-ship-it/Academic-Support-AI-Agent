from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PDF_FILE_NAME = "SỔ TAY SV - Bách Khoa - NĂM HỌC 2025-2026.pdf"
FAQ_FILE_NAME = "faq_hcmut.jsonl"

DEFAULT_PDF_PATH = DATA_DIR / PDF_FILE_NAME
DEFAULT_FAQ_PATH = DATA_DIR / FAQ_FILE_NAME


def _resolve_data_path(path: str | Path, fallback_name: str) -> Path:
    """Ưu tiên `data/`, nhưng vẫn fallback về root nếu file chưa được di chuyển."""
    path = Path(path)
    if path.exists():
        return path

    root_path = PROJECT_ROOT / fallback_name
    if root_path.exists():
        return root_path

    return path


def load_pdf_documents(pdf_path: str | Path = DEFAULT_PDF_PATH) -> list[Document]:
    """Load PDF với chiến lược hi_res để nhận diện tiêu đề và bảng biểu tốt hơn."""
    pdf_path = _resolve_data_path(pdf_path, PDF_FILE_NAME)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file PDF: {pdf_path}")

    loader = UnstructuredPDFLoader(
        str(pdf_path),
        strategy="hi_res",
        mode="elements",
        languages=["vie"],
    )
    return loader.load()


def load_faq_documents(faq_path: str | Path = DEFAULT_FAQ_PATH) -> list[Document]:
    """Load FAQ JSONL và giữ metadata quan trọng để Agent có thể filter sau này."""
    faq_path = _resolve_data_path(faq_path, FAQ_FILE_NAME)
    if not faq_path.exists():
        return []

    documents: list[Document] = []
    with faq_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            item = json.loads(line)
            question = item.get("question", "")
            answer = item.get("answer", "")
            content = f"Câu hỏi: {question}\nTrả lời: {answer}"
            metadata = {
                "source": str(faq_path),
                "source_name": "faq_hcmut",
                "row_number": line_number,
                "id": item.get("id", ""),
                "school": item.get("school", ""),
                "category": item.get("category", ""),
            }
            documents.append(Document(page_content=content, metadata=metadata))

    return documents


def split_documents(
    documents: Iterable[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[Document]:
    """
    Chunking ưu tiên giữ cấu trúc PHẦN/Điều/Khoản của sổ tay sinh viên.

    So với bản thử nghiệm ban đầu, chunk nhỏ hơn giúp retrieval tập trung hơn,
    overlap vừa đủ để không làm đứt ngữ cảnh giữa các đoạn liền nhau.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\nPHẦN", "\nĐiều", "\nKhoản", "\n", ".", " ", ""],
    )
    return text_splitter.split_documents(list(documents))


def prepare_data(
    pdf_path: str | Path = DEFAULT_PDF_PATH,
    faq_path: str | Path = DEFAULT_FAQ_PATH,
    include_faq: bool = True,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[Document]:
    """Load PDF/FAQ, chia chunk và gắn metadata ổn định cho vector database."""
    print("--- Bắt đầu xử lý dữ liệu ---")

    documents = load_pdf_documents(pdf_path)
    if include_faq:
        faq_documents = load_faq_documents(faq_path)
        documents.extend(faq_documents)
        print(f"Đã load {len(faq_documents)} FAQ.")

    chunks = split_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    for index, chunk in tqdm(
        enumerate(chunks),
        total=len(chunks),
        desc="Gắn metadata",
    ):
        chunk.metadata.setdefault("source_name", "so_tay_sv")
        chunk.metadata["chunk_id"] = index
        chunk.metadata.setdefault("page_number", 0)

    print(f"Hoàn thành. Tổng số chunks: {len(chunks)}")
    return chunks
