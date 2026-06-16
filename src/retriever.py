from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_DIR = PROJECT_ROOT / "huit_db"
DEFAULT_COLLECTION = "huit_academic_chunks"
DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_RAW_K = 30


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None
    vector_score: float
    policy_boost: float
    rerank_score: float


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def _vector_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + max(distance, 0.0))


def _normalize_text(value: Any) -> str:
    text = str(value or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _metadata_search_text(metadata: dict[str, Any], document: str) -> str:
    fields = [
        metadata.get("document_title"),
        metadata.get("article_title"),
        metadata.get("section_heading"),
        metadata.get("form_code"),
        metadata.get("form_name"),
        metadata.get("related_procedure"),
        document[:500],
    ]
    return _normalize_text(" ".join(str(field or "") for field in fields))


def _asks_for_form(query: str) -> bool:
    normalized = _normalize_text(query)
    return any(term in normalized for term in ("bieu mau", "phieu", "mau"))


ARTICLE_HINT_RULES: tuple[tuple[str, str], ...] = (
    ("duoc hieu la gi|giai thich tu ngu|chuong trinh dao tao duoc hieu", "2"),
    ("clo|plo|chuan dau ra hoc phan|chuan dau ra chuong trinh", "3"),
    ("hoc phan bat buoc|hoc phan tu chon|hoc phan thay the|hoc phan tien quyet|hoc phan truoc|hoc phan song hanh", "6"),
    ("phuong thuc tin chi|to chuc dao tao theo phuong thuc|dao tao theo phuong thuc tin chi", "7"),
    ("truc tuyen|online|thi truc tuyen|danh gia truc tuyen", "8"),
    ("van bang thu hai|lien thong dai hoc|du thinh", "10"),
    ("trach nhiem", "11"),
    ("quyen gi|quyen cua sinh vien|nguoi hoc co nhung quyen", "12"),
    ("de cuong hoc phan|chuong trinh dao tao gom|muc tieu chuan dau ra va de cuong", "14"),
    ("chuong trinh dao tao thay doi|cap nhat chuong trinh|cong bo chuong trinh", "15"),
    ("nang luc toi thieu|kien thuc ky nang va trach nhiem|sau tot nghiep gom kien thuc", "16"),
    ("ke hoach giang day|ke hoach hoc tap", "17"),
    ("thoi gian thiet ke|thoi gian toi da|van bang thu hai cap bang ky su|dai hoc chinh quy cap bang ky su", "18"),
    ("nhap hoc|the sinh vien|tai khoan ca nhan|sinh hoat cong dan", "19"),
    ("giai doan giao duc dai cuong|nguyen vong nganh|sap xep vao hoc", "20"),
    ("hoc ky he|so tin chi toi thieu|so tin chi toi da|toi da bao nhieu tin chi|duoc dang ky toi da|dang ky khoi luong|chua dong hoc phi|dong hoc phi dung han", "21"),
    ("rut hoc phan|hoan hoc phi", "22"),
    ("nghi om|tai nan|viec rieng|25 so gio", "23"),
    ("tam dung hoc tap|tiep nhan lai|nhu cau ca nhan", "24"),
    ("chuyen nganh|chuyen nganh may lan", "25"),
    ("trao doi sinh vien|cong nhan tin chi giua", "26"),
    ("hoc cung luc hai chuong trinh|song nganh|chuong trinh thu nhat", "27"),
    ("chuyen truong", "28"),
    ("canh bao hoc vu|buoc thoi hoc|het thoi gian dao tao toi da|chuyen sang he vua lam vua hoc", "29"),
    ("thang diem|diem thanh phan|diem qua trinh|diem i|b+|rt|diem h|hoc phan cot loi|thi lai|danh gia lai", "30"),
    ("mien giam hoc phan|cong nhan diem|chuyen diem|truoc dang ky hoc phan|50 chuong trinh", "31"),
    ("gpa|diem trung binh chung|ai va ni|diem chu sang thang diem 4", "32"),
    ("phuc khao|khieu nai diem", "33"),
    ("thong bao diem|xac nhan ket qua hoc tap|ket qua hoc ky|cong bo va luu tru", "34"),
    ("xep hang nam dao tao|nam thu hai|nam thu ba|nam thu tu|hang hoc luc", "35"),
    ("cong nhan ket qua hoc tap|chuyen doi|50 khoi luong", "36"),
    ("hoi dong cham khoa luan|khoa luan tot nghiep toi thieu", "37"),
    ("ket qua cham khoa luan|cong bo trong bao lau|7 ngay", "38"),
    ("dieu kien xet tot nghiep|khong nop phieu|le tot nghiep|thang 4|thang 10", "39"),
    ("xep loai tot nghiep|5 tin chi|5%|ky luat canh cao|giam hang", "40"),
    ("giay chung nhan tot nghiep|bang tot nghiep|phu luc van bang|03 nam|3 nam tinh tu khi thoi hoc", "41"),
    ("bang diem goc|so goc cap phat bang|quyet dinh trung tuyen", "42"),
    ("thanh tra|kiem tra cong tac dao tao", "43"),
    ("khen thuong|thanh tich trong dao tao", "44"),
)


def _article_hints(query: str) -> set[str]:
    query_norm = _normalize_text(query)
    hints: set[str] = set()
    for pattern, article_number in ARTICLE_HINT_RULES:
        if any(part in query_norm for part in pattern.split("|")):
            hints.add(article_number)
    return hints


def _lexical_boost(metadata: dict[str, Any], query: str, document: str, intent: str) -> float:
    query_norm = _normalize_text(query)
    searchable = _metadata_search_text(metadata, document)
    source_type = metadata.get("source_type")
    asks_for_form = any(term in query_norm for term in ("bieu mau", "phieu", "mau", "don"))
    boost = 0.0

    targeted_rules = [
        ("trach nhiem", "11", None, 0.55),
        ("hoc phan cot loi", "30", None, 0.55),
        ("diem i", "30", None, 0.55),
        ("chuong trinh dao tao thay doi", "15", None, 0.45),
        ("duoc dang ky toi da", "21", None, 0.55),
        ("toi da bao nhieu tin chi", "21", None, 0.55),
        ("xac nhan ket qua hoc tap", "34", None, 0.55),
        ("ket qua hoc tap hoc ky", "34", None, 0.55),
        ("thoi han hoan thien", "41", None, 0.65),
        ("gdqp", "41", None, 0.35),
        ("gdtc", "41", None, 0.35),
        ("dieu kien xet tot nghiep", "39", None, 0.55),
        ("tro lai hoc tap", None, "BM02", 0.55),
        ("chuyen nganh", None, "BM03", 0.55),
        ("hoc cung luc hai chuong trinh", None, "BM04", 0.55),
        ("mien giam", None, "BM11", 0.55),
        ("cong nhan diem", None, "BM11", 0.55),
        ("xet tot nghiep", None, "BM12", 0.35),
    ]
    for phrase, article_number, form_code, value in targeted_rules:
        if phrase not in query_norm:
            continue
        if article_number and str(metadata.get("article_number")) == article_number:
            boost += value
        if form_code and asks_for_form and str(metadata.get("form_code")) == form_code:
            boost += value

    if intent == "current_policy" and str(metadata.get("article_number")) in _article_hints(query):
        boost += 0.7

    title_text = _normalize_text(
        " ".join(
            str(field or "")
            for field in (
                metadata.get("article_title"),
                metadata.get("section_heading"),
                metadata.get("form_name"),
                metadata.get("related_procedure"),
            )
        )
    )
    query_tokens = {
        token
        for token in query_norm.split()
        if len(token) >= 3
        and token
        not in {
            "huit",
            "sinh",
            "vien",
            "muon",
            "dung",
            "the",
            "nao",
            "can",
            "quy",
            "dinh",
            "hoc",
            "tap",
            "cho",
            "cua",
            "tai",
        }
    }
    overlap = query_tokens & set(title_text.split())
    if overlap:
        boost += min(0.22, 0.045 * len(overlap))

    if source_type == "form" and asks_for_form and metadata.get("related_procedure"):
        procedure = _normalize_text(metadata.get("related_procedure"))
        if procedure and procedure in query_norm:
            boost += 0.25
    if source_type == "regulation" and any(token in searchable for token in query_tokens):
        boost += 0.05

    return boost


def _policy_boost(metadata: dict[str, Any], intent: str, query: str, document: str) -> float:
    source_type = metadata.get("source_type")
    priority_score = float(metadata.get("priority_score") or 0)
    is_current = _as_bool(metadata.get("is_current"))
    use_as_primary = _as_bool(metadata.get("use_as_primary_legal_source", True))

    boost = min(priority_score, 100.0) / 100.0 * 0.25
    if is_current:
        boost += 0.08

    if intent == "current_policy":
        if source_type == "regulation":
            boost += 0.28
        if source_type == "faq" or not use_as_primary:
            boost -= 0.22
        if _as_bool(metadata.get("superseded_risk")):
            boost -= 0.25
    elif intent == "procedure":
        if source_type == "guidance":
            boost += 0.22
        if source_type == "form":
            boost += 0.16
        if source_type == "regulation":
            boost += 0.08
        if source_type == "faq":
            boost -= 0.08
    elif intent in {"historical", "historical_comparison", "legacy_policy"}:
        if source_type == "historical_or_warning_source":
            boost += 0.46
        if source_type == "regulation":
            boost += 0.08
        if source_type == "faq":
            boost -= 0.12

    boost += _lexical_boost(metadata, query, document, intent)

    normalized_query = _normalize_text(query)
    searchable_text = _metadata_search_text(metadata, document)
    asks_for_steps = any(term in normalized_query for term in ("quy trinh", "lam the nao", "lam thu tuc", "thu tuc", "thuc hien", "cac buoc"))
    if intent == "procedure" and source_type == "guidance" and asks_for_steps:
        boost += 0.28
    if intent == "procedure" and source_type == "regulation" and asks_for_steps:
        boost -= 0.16
    if intent == "procedure" and source_type == "form" and not _asks_for_form(query):
        boost -= 0.25
    if _asks_for_form(query):
        if source_type == "form":
            boost += 0.38
        if source_type == "guidance":
            boost += 0.08
        if "xet tot nghiep" in normalized_query:
            if "tot nghiep" in searchable_text:
                boost += 0.2

    return boost


class HUITAcademicRetriever:
    def __init__(
        self,
        db_dir: str | Path = DEFAULT_DB_DIR,
        collection_name: str = DEFAULT_COLLECTION,
        model_name: str | None = None,
        raw_k: int = DEFAULT_RAW_K,
    ) -> None:
        self.db_dir = Path(db_dir)
        self.collection_name = collection_name
        self.model_name = model_name or os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL)
        self.raw_k = raw_k
        self.model = SentenceTransformer(self.model_name)
        self.client = chromadb.PersistentClient(path=str(self.db_dir))
        self.collection = self.client.get_collection(self.collection_name)

    def search(self, query: str, intent: str = "current_policy", k: int = 5) -> list[RetrievalResult]:
        query_embedding = self.model.encode([query], normalize_embeddings=True).tolist()[0]
        responses = [
            self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max(self.raw_k, k),
                include=["documents", "metadatas", "distances"],
            )
        ]
        if intent == "current_policy":
            responses.append(
                self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=max(24, self.raw_k),
                    where={"source_type": "regulation"},
                    include=["documents", "metadatas", "distances"],
                )
            )
        if intent in {"historical", "historical_comparison", "legacy_policy"}:
            responses.append(
                self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=max(12, k),
                    where={"source_type": "historical_or_warning_source"},
                    include=["documents", "metadatas", "distances"],
                )
            )
        if _asks_for_form(query):
            responses.append(
                self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=20,
                    where={"source_type": "form"},
                    include=["documents", "metadatas", "distances"],
                )
            )
        for article_number in _article_hints(query):
            responses.append(
                self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=8,
                    where={"article_number": article_number},
                    include=["documents", "metadatas", "distances"],
                )
            )

        candidates: list[RetrievalResult] = []
        seen_ids: set[str] = set()
        for response in responses:
            for index, chunk_id in enumerate(response["ids"][0]):
                if chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk_id)
                text = response["documents"][0][index]
                metadata = response["metadatas"][0][index]
                distance = response["distances"][0][index]
                vector_score = _vector_score(distance)
                policy_boost = _policy_boost(metadata, intent, query, text)
                candidates.append(
                    RetrievalResult(
                        chunk_id=chunk_id,
                        text=text,
                        metadata=metadata,
                        distance=distance,
                        vector_score=round(vector_score, 6),
                        policy_boost=round(policy_boost, 6),
                        rerank_score=round(vector_score + policy_boost, 6),
                    )
                )

        candidates.sort(key=lambda item: item.rerank_score, reverse=True)
        return candidates[:k]


_DEFAULT_RETRIEVER: HUITAcademicRetriever | None = None


def get_default_retriever() -> HUITAcademicRetriever:
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        _DEFAULT_RETRIEVER = HUITAcademicRetriever()
    return _DEFAULT_RETRIEVER


def search_academic_policy(query: str, intent: str = "current_policy", k: int = 5) -> list[dict[str, Any]]:
    results = get_default_retriever().search(query=query, intent=intent, k=k)
    return [
        {
            "chunk_id": result.chunk_id,
            "text": result.text,
            "metadata": result.metadata,
            "distance": result.distance,
            "vector_score": result.vector_score,
            "policy_boost": result.policy_boost,
            "rerank_score": result.rerank_score,
            "citation": result.metadata.get("citation"),
        }
        for result in results
    ]
