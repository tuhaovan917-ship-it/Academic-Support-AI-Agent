from __future__ import annotations

from typing import Any

from src.retriever import search_academic_policy


def retrieve(query: str, intent: str = "current_policy", k: int = 5) -> list[dict[str, Any]]:
    results = search_academic_policy(query=query, intent=intent, k=k)
    return [
        {
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("metadata", {}).get("document_id"),
            "source_type": item.get("metadata", {}).get("source_type"),
            "article_number": item.get("metadata", {}).get("article_number"),
            "form_code": item.get("metadata", {}).get("form_code"),
            "citation": item.get("citation"),
            "text": item.get("text", ""),
            "score": item.get("rerank_score"),
            "metadata": item.get("metadata", {}),
        }
        for item in results
    ]
