from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHUNKS_PATH = PROJECT_ROOT / "data" / "review" / "approved_chunks.jsonl"
DEFAULT_DB_DIR = PROJECT_ROOT / "huit_db"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "intermediate" / "vector_upsert_summary.json"
DEFAULT_COLLECTION = "huit_academic_chunks"
DEFAULT_MODEL = "BAAI/bge-m3"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def normalize_metadata_value(value: Any) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalize_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    return {key: normalize_metadata_value(value) for key, value in metadata.items()}


def build_chroma_payload(chunks: list[dict[str, Any]]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    for chunk in chunks:
        ids.append(chunk["chunk_id"])
        documents.append(chunk["text"])
        metadata = dict(chunk.get("metadata", {}))
        metadata["unit_type"] = chunk.get("unit_type")
        metadata["unit_key"] = chunk.get("unit_key")
        metadata["review_status"] = chunk.get("review_gate", {}).get("status", "approved")
        metadatas.append(normalize_metadata(metadata))
    return ids, documents, metadatas


def batch_ranges(total: int, batch_size: int) -> list[range]:
    return [range(start, min(start + batch_size, total)) for start in range(0, total, batch_size)]


def upsert_chunks(
    chunks: list[dict[str, Any]],
    db_dir: Path,
    collection_name: str,
    model_name: str,
    batch_size: int,
) -> dict[str, Any]:
    ids, documents, metadatas = build_chroma_payload(chunks)
    model = SentenceTransformer(model_name)
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "school": "HUIT",
            "embedding_model": model_name,
            "source": "data/review/approved_chunks.jsonl",
        },
    )

    for batch in batch_ranges(len(documents), batch_size):
        batch_documents = [documents[index] for index in batch]
        embeddings = model.encode(
            batch_documents,
            batch_size=min(batch_size, 32),
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()
        collection.upsert(
            ids=[ids[index] for index in batch],
            documents=batch_documents,
            metadatas=[metadatas[index] for index in batch],
            embeddings=embeddings,
        )

    return {
        "collection_name": collection_name,
        "persist_directory": str(db_dir.relative_to(PROJECT_ROOT)),
        "embedding_model": model_name,
        "collection_count": collection.count(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert approved HUIT chunks into a local ChromaDB.")
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--model", default=os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL))
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--reset", action="store_true", help="Delete the target Chroma directory before upsert.")
    args = parser.parse_args()

    if args.reset and args.db_dir.exists():
        shutil.rmtree(args.db_dir)
    args.db_dir.mkdir(parents=True, exist_ok=True)

    chunks = load_jsonl(args.chunks_path)
    result = upsert_chunks(
        chunks=chunks,
        db_dir=args.db_dir,
        collection_name=args.collection,
        model_name=args.model,
        batch_size=args.batch_size,
    )

    summary = {
        "chunks_path": display_path(args.chunks_path),
        "total_input_chunks": len(chunks),
        **result,
        "source_type_counts": dict(Counter(chunk["metadata"].get("source_type") for chunk in chunks)),
        "unit_type_counts": dict(Counter(chunk.get("unit_type") for chunk in chunks)),
        "document_counts": dict(Counter(chunk["document_id"] for chunk in chunks)),
    }
    write_json(args.summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
