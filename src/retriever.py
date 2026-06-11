from __future__ import annotations

import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHROMA_DIR = PROJECT_ROOT / "chroma_db"
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-base"


def get_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=model_name)


def _delete_chroma_dir(persist_directory: Path) -> None:
    resolved_dir = persist_directory.resolve()
    project_root = PROJECT_ROOT.resolve()
    if project_root not in resolved_dir.parents and resolved_dir != project_root:
        raise ValueError(f"Từ chối xóa thư mục nằm ngoài project: {resolved_dir}")
    shutil.rmtree(resolved_dir)


def setup_vector_db(
    chunks: list[Document],
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    reset: bool = False,
) -> Chroma:
    """Tạo và lưu Chroma vector database từ danh sách chunks."""
    if not chunks:
        raise ValueError("Danh sách chunks đang rỗng, không thể tạo vector DB.")

    persist_directory = Path(persist_directory)
    if reset and persist_directory.exists():
        _delete_chroma_dir(persist_directory)

    embedding_model = get_embedding_model(model_name)
    cleaned_chunks = filter_complex_metadata(chunks)

    return Chroma.from_documents(
        documents=cleaned_chunks,
        embedding=embedding_model,
        persist_directory=str(persist_directory),
    )


def load_vector_db(
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> Chroma:
    """Load Chroma vector database đã có sẵn."""
    persist_directory = Path(persist_directory)
    if not persist_directory.exists():
        raise FileNotFoundError(f"Không tìm thấy Chroma DB: {persist_directory}")

    embedding_model = get_embedding_model(model_name)
    return Chroma(
        persist_directory=str(persist_directory),
        embedding_function=embedding_model,
    )


def search(
    query: str,
    k: int = 5,
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
) -> list[Document]:
    vector_db = load_vector_db(persist_directory=persist_directory)
    return vector_db.similarity_search(query, k=k)
