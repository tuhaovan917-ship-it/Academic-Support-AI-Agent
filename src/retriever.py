from __future__ import annotations

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_CHROMA_DIR = PROJECT_ROOT / "hcmut_nttu_db"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"


def _get_embedding_device() -> str:
    configured_device = os.getenv("EMBEDDING_DEVICE")
    if configured_device:
        return configured_device

    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def get_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": _get_embedding_device()},
        encode_kwargs={"normalize_embeddings": True},
    )


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
    """Tạo và lưu Chroma vector database từ danh sách chunks đã enrich metadata."""
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

    return Chroma(
        persist_directory=str(persist_directory),
        embedding_function=get_embedding_model(model_name),
    )


def _metadata_filter(school: str | None = None) -> dict[str, str] | None:
    if not school:
        return None
    return {"school": school.upper()}


def load_documents_from_vector_db(
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    school: str | None = None,
) -> list[Document]:
    vector_db = load_vector_db(
        persist_directory=persist_directory,
        model_name=model_name,
    )
    raw = vector_db.get(include=["documents", "metadatas"])
    documents = raw.get("documents") or []
    metadatas = raw.get("metadatas") or []

    loaded = [
        Document(page_content=content, metadata=metadata or {})
        for content, metadata in zip(documents, metadatas)
        if content
    ]
    if school:
        school = school.upper()
        loaded = [
            document
            for document in loaded
            if document.metadata.get("school", "").upper() == school
        ]
    return loaded


def get_hybrid_retriever(
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    k: int = 5,
    school: str | None = None,
    bm25_weight: float = 0.6,
    vector_weight: float = 0.4,
) -> EnsembleRetriever:
    documents = load_documents_from_vector_db(
        persist_directory=persist_directory,
        model_name=model_name,
        school=school,
    )
    if not documents:
        raise ValueError("Vector DB không có document nào để tạo BM25 retriever.")

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = k

    vector_db = load_vector_db(
        persist_directory=persist_directory,
        model_name=model_name,
    )
    search_kwargs: dict[str, object] = {"k": k}
    metadata_filter = _metadata_filter(school)
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter
    vector_retriever = vector_db.as_retriever(search_kwargs=search_kwargs)

    return EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[bm25_weight, vector_weight],
    )


def vector_search(
    query: str,
    k: int = 5,
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
    school: str | None = None,
) -> list[Document]:
    vector_db = load_vector_db(persist_directory=persist_directory)
    return vector_db.similarity_search(
        query,
        k=k,
        filter=_metadata_filter(school),
    )


def hybrid_search(
    query: str,
    k: int = 5,
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
    school: str | None = None,
) -> list[Document]:
    retriever = get_hybrid_retriever(
        persist_directory=persist_directory,
        k=k,
        school=school,
    )
    return retriever.invoke(query)[:k]


def search(
    query: str,
    k: int = 5,
    persist_directory: str | Path = DEFAULT_CHROMA_DIR,
    school: str | None = None,
) -> list[Document]:
    return hybrid_search(
        query=query,
        k=k,
        persist_directory=persist_directory,
        school=school,
    )
