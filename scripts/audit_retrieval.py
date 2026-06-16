from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_DIR = PROJECT_ROOT / "huit_db"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "review" / "retrieval_audit_report.json"
DEFAULT_MARKDOWN_PATH = PROJECT_ROOT / "data" / "review" / "retrieval_audit_report.md"
DEFAULT_CASES_PATH = PROJECT_ROOT / "data" / "review" / "audit_cases.jsonl"
DEFAULT_COLLECTION = "huit_academic_chunks"
DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_RAW_K = 30


AUDIT_CASES = [
    {
        "case_id": "graduation_5_percent_retake",
        "query": "Xếp loại tốt nghiệp có bị giảm nếu học lại quá 5% tín chỉ không?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "40",
    },
    {
        "case_id": "course_cancellation_procedure",
        "query": "Sinh viên muốn hủy học phần thì làm thế nào?",
        "intent": "procedure",
        "expected_document_id": "huit_guidance_course_registration_2026",
    },
    {
        "case_id": "major_transfer_conditions",
        "query": "Điều kiện chuyển ngành đào tạo là gì?",
        "intent": "procedure",
        "expected_document_id": "huit_guidance_academic_status_2026",
    },
    {
        "case_id": "graduation_application_form",
        "query": "Muốn xét tốt nghiệp thì dùng biểu mẫu nào?",
        "intent": "procedure",
        "expected_document_id": "huit_form_bm12_graduation_application",
    },
    {
        "case_id": "academic_warning",
        "query": "Khi nào sinh viên bị cảnh báo học vụ?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
    },
    {
        "case_id": "course_score_scale",
        "query": "Thang điểm đánh giá kết quả học tập học phần tại HUIT như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
    },
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def vector_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + max(distance, 0.0))


def normalize_text(value: Any) -> str:
    text = str(value or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


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


def article_hints(query: str) -> set[str]:
    query_norm = normalize_text(query)
    hints: set[str] = set()
    for pattern, article_number in ARTICLE_HINT_RULES:
        if any(part in query_norm for part in pattern.split("|")):
            hints.add(article_number)
    return hints


def metadata_search_text(metadata: dict[str, Any], document: str) -> str:
    fields = [
        metadata.get("document_title"),
        metadata.get("article_title"),
        metadata.get("section_heading"),
        metadata.get("form_code"),
        metadata.get("form_name"),
        metadata.get("related_procedure"),
        document[:500],
    ]
    return normalize_text(" ".join(str(field or "") for field in fields))


def lexical_boost(metadata: dict[str, Any], query: str, document: str, intent: str) -> float:
    query_norm = normalize_text(query)
    searchable = metadata_search_text(metadata, document)
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

    if intent == "current_policy" and str(metadata.get("article_number")) in article_hints(query):
        boost += 0.7

    title_text = normalize_text(
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
        procedure = normalize_text(metadata.get("related_procedure"))
        if procedure and procedure in query_norm:
            boost += 0.25
    if source_type == "regulation" and any(token in searchable for token in query_tokens):
        boost += 0.05

    return boost


def policy_boost(metadata: dict[str, Any], intent: str, query: str, document: str) -> float:
    source_type = metadata.get("source_type")
    priority_score = float(metadata.get("priority_score") or 0)
    is_current = metadata.get("is_current")
    use_as_primary = metadata.get("use_as_primary_legal_source")

    boost = 0.0
    boost += min(priority_score, 100.0) / 100.0 * 0.25
    if is_current is True or str(is_current).lower() == "true":
        boost += 0.08

    if intent == "current_policy":
        if source_type == "regulation":
            boost += 0.28
        if source_type == "faq" or use_as_primary is False or str(use_as_primary).lower() == "false":
            boost -= 0.22
        if metadata.get("superseded_risk"):
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

    boost += lexical_boost(metadata, query, document, intent)

    normalized_query = normalize_text(query)
    searchable_text = metadata_search_text(metadata, document)
    asks_for_form = any(term in normalized_query for term in ("bieu mau", "phieu", "mau"))
    asks_for_steps = any(term in normalized_query for term in ("quy trinh", "lam the nao", "lam thu tuc", "thu tuc", "thuc hien", "cac buoc"))
    if intent == "procedure" and source_type == "guidance" and asks_for_steps:
        boost += 0.28
    if intent == "procedure" and source_type == "regulation" and asks_for_steps:
        boost -= 0.16
    if intent == "procedure" and source_type == "form" and not asks_for_form:
        boost -= 0.25
    if asks_for_form:
        if source_type == "form":
            boost += 0.38
        if source_type == "guidance":
            boost += 0.08
        if "xet tot nghiep" in normalized_query:
            if "tot nghiep" in searchable_text:
                boost += 0.2

    return boost


def rerank_result(result: dict[str, Any], intent: str, query: str) -> dict[str, Any]:
    metadata = result["metadata"]
    base = vector_score(result.get("distance"))
    boost = policy_boost(metadata, intent, query, result.get("document", ""))
    score = base + boost
    return {
        **result,
        "vector_score": round(base, 6),
        "policy_boost": round(boost, 6),
        "rerank_score": round(score, 6),
    }


def query_collection(
    collection: Any,
    model: SentenceTransformer,
    query: str,
    intent: str,
    raw_k: int,
    final_k: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    embedding = model.encode([query], normalize_embeddings=True).tolist()[0]

    responses = [
        collection.query(
            query_embeddings=[embedding],
            n_results=raw_k,
            include=["documents", "metadatas", "distances"],
        )
    ]

    if intent == "current_policy":
        responses.append(
            collection.query(
                query_embeddings=[embedding],
                n_results=max(24, raw_k),
                where={"source_type": "regulation"},
                include=["documents", "metadatas", "distances"],
            )
        )
    if intent in {"historical", "historical_comparison", "legacy_policy"}:
        responses.append(
            collection.query(
                query_embeddings=[embedding],
                n_results=max(12, final_k),
                where={"source_type": "historical_or_warning_source"},
                include=["documents", "metadatas", "distances"],
            )
        )

    normalized_query = normalize_text(query)
    if any(term in normalized_query for term in ("bieu mau", "phieu", "mau")):
        responses.append(
            collection.query(
                query_embeddings=[embedding],
                n_results=20,
                where={"source_type": "form"},
                include=["documents", "metadatas", "distances"],
            )
        )

    for article_number in article_hints(query):
        responses.append(
            collection.query(
                query_embeddings=[embedding],
                n_results=8,
                where={"article_number": article_number},
                include=["documents", "metadatas", "distances"],
            )
        )

    raw_results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for response in responses:
        for index, chunk_id in enumerate(response["ids"][0]):
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            raw_results.append(
                {
                    "rank": len(raw_results) + 1,
                    "chunk_id": chunk_id,
                    "document": response["documents"][0][index],
                    "metadata": response["metadatas"][0][index],
                    "distance": response["distances"][0][index],
                }
            )

    reranked = [rerank_result(result, intent, query) for result in raw_results]
    reranked.sort(key=lambda item: item["rerank_score"], reverse=True)
    for index, result in enumerate(reranked, start=1):
        result["rerank"] = index
    return raw_results[:final_k], reranked[:final_k]


def case_passed(case: dict[str, Any], reranked: list[dict[str, Any]]) -> bool:
    if case.get("expected_status") in {"pending_source", "discarded_source"}:
        return True
    if not reranked:
        return False
    top = reranked[0]
    metadata = top["metadata"]
    if case.get("expected_document_id") and metadata.get("document_id") != case["expected_document_id"]:
        return False
    if case.get("expected_article_number") and str(metadata.get("article_number")) != str(case["expected_article_number"]):
        return False
    if case.get("expected_form_code") and str(metadata.get("form_code")) != str(case["expected_form_code"]):
        return False
    if case.get("expected_source_type") and str(metadata.get("source_type")) != str(case["expected_source_type"]):
        return False
    return True


def summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result["metadata"]
    return {
        "rank": result.get("rank"),
        "rerank": result.get("rerank"),
        "chunk_id": result["chunk_id"],
        "document_id": metadata.get("document_id"),
        "source_type": metadata.get("source_type"),
        "unit_type": metadata.get("unit_type"),
        "priority_score": metadata.get("priority_score"),
        "citation": metadata.get("citation"),
        "distance": result.get("distance"),
        "vector_score": result.get("vector_score"),
        "policy_boost": result.get("policy_boost"),
        "rerank_score": result.get("rerank_score"),
        "preview": result["document"][:350],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Retrieval Audit Report",
        "",
        f"- Collection: `{report['collection_name']}`",
        f"- Persist directory: `{report['persist_directory']}`",
        f"- Embedding model: `{report['embedding_model']}`",
        f"- Collection count: `{report['collection_count']}`",
        f"- Passed cases: `{report['passed_cases']}/{report['total_cases']}`",
        f"- Pending-source cases: `{report['pending_source_cases']}`",
        f"- Discarded-source cases: `{report.get('discarded_source_cases', 0)}`",
        "",
        "## Cases",
        "",
    ]
    for case in report["cases"]:
        lines.extend(
            [
                f"### {case['case_id']}",
                "",
                f"- Query: {case['query']}",
                f"- Intent: `{case['intent']}`",
                f"- Expected status: `{case.get('expected_status', 'active')}`",
                f"- Passed: `{case['passed']}`",
                "",
                "| Rank | Doc | Source | Citation | Score |",
                "|---:|---|---|---|---:|",
            ]
        )
        for result in case["reranked_results"]:
            lines.append(
                "| {rank} | {doc} | {source} | {citation} | {score} |".format(
                    rank=result["rerank"],
                    doc=result.get("document_id", ""),
                    source=result.get("source_type", ""),
                    citation=(result.get("citation") or "").replace("|", "\\|"),
                    score=result.get("rerank_score"),
                )
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit HUIT Chroma retrieval and priority reranking.")
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--model", default=os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL))
    parser.add_argument("--cases-path", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--raw-k", type=int, default=DEFAULT_RAW_K)
    parser.add_argument("--final-k", type=int, default=5)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--markdown-path", type=Path, default=DEFAULT_MARKDOWN_PATH)
    args = parser.parse_args()

    model = SentenceTransformer(args.model)
    client = chromadb.PersistentClient(path=str(args.db_dir))
    collection = client.get_collection(args.collection)

    audit_cases = load_jsonl(args.cases_path) if args.cases_path.exists() else AUDIT_CASES
    cases: list[dict[str, Any]] = []
    for case in audit_cases:
        if case.get("expected_status") in {"pending_source", "discarded_source"}:
            raw_results, reranked = [], []
            passed = True
            cases.append(
                {
                    **case,
                    "passed": passed,
                    "raw_top_results": [],
                    "reranked_results": [],
                }
            )
            continue
        raw_results, reranked = query_collection(
            collection=collection,
            model=model,
            query=case["query"],
            intent=case["intent"],
            raw_k=args.raw_k,
            final_k=args.final_k,
        )
        passed = case_passed(case, reranked)
        cases.append(
            {
                **case,
                "passed": passed,
                "raw_top_results": [summarize_result(result) for result in raw_results],
                "reranked_results": [summarize_result(result) for result in reranked],
            }
        )

    passed_count = sum(1 for case in cases if case["passed"])
    pending_count = sum(1 for case in cases if case.get("expected_status") == "pending_source")
    discarded_count = sum(1 for case in cases if case.get("expected_status") == "discarded_source")
    report = {
        "collection_name": args.collection,
        "persist_directory": str(args.db_dir.relative_to(PROJECT_ROOT)),
        "embedding_model": args.model,
        "cases_path": str(args.cases_path.relative_to(PROJECT_ROOT)) if args.cases_path.exists() else None,
        "collection_count": collection.count(),
        "total_cases": len(cases),
        "passed_cases": passed_count,
        "failed_cases": len(cases) - passed_count,
        "active_cases": len(cases) - pending_count - discarded_count,
        "pending_source_cases": pending_count,
        "discarded_source_cases": discarded_count,
        "cases": cases,
    }
    write_json(args.summary_path, report)
    write_text(args.markdown_path, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed_count == len(cases) else 2


if __name__ == "__main__":
    sys.exit(main())
