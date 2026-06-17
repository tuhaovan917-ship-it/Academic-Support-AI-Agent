from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import run_agent


REPORT_JSON = PROJECT_ROOT / "data" / "review" / "stage2b_hybrid_audit.json"
REPORT_MD = PROJECT_ROOT / "data" / "review" / "stage2b_hybrid_audit.md"


@dataclass
class AuditCase:
    case_id: str
    query: str
    category: str
    expected_routes: set[str]
    expected_statuses: set[str] = field(default_factory=lambda: {"answered"})
    session_id: str | None = None
    require_citation: bool = False
    require_tool: bool = False
    require_planner: bool = True
    require_answer_any: list[str] = field(default_factory=list)
    require_answer_all: list[str] = field(default_factory=list)
    require_citation_any: list[str] = field(default_factory=list)
    forbid_answer_any: list[str] = field(default_factory=list)
    forbid_documents: list[str] = field(default_factory=list)
    require_article40_constraints: bool = False
    require_form_place: bool = False


def cases() -> list[AuditCase]:
    return [
        AuditCase("grade_01", "6.8 đổi sang điểm chữ và hệ 4", "grade_policy", {"policy_retrieval"}, require_citation=True, require_answer_all=["C+", "2.5"], require_citation_any=["Điều 30"]),
        AuditCase("grade_02", "Điểm A là từ mấy đến mấy?", "grade_policy", {"policy_retrieval"}, require_citation=True, require_answer_all=["8.5", "10.0"], require_citation_any=["Điều 30"]),
        AuditCase("grade_03", "Bao nhiêu điểm hệ số 10 mới được điểm B+?", "grade_policy", {"policy_retrieval"}, require_citation=True, require_answer_all=["8.0", "8.4"], require_citation_any=["Điều 30"]),
        AuditCase("grade_04", "Điểm F có tính là 0 không?", "grade_policy", {"policy_retrieval"}, require_citation=True, require_answer_any=["0", "F"], require_citation_any=["Điều 30"]),
        AuditCase("grade_05", "Điểm I là gì?", "grade_policy", {"policy_retrieval"}, require_citation=True, require_answer_any=["I", "chưa"], require_citation_any=["Điều 30"]),
        AuditCase("grade_06", "Điểm RT có tính GPA không?", "grade_policy", {"policy_retrieval"}, require_citation=True, require_answer_any=["RT", "Không tính"], require_citation_any=["Điều 30"]),
        AuditCase("grade_07", "Điểm học phần được làm tròn thế nào?", "grade_policy", {"policy_retrieval"}, require_citation=True, require_answer_any=["làm tròn", "một chữ số"], require_citation_any=["Điều 30"]),
        AuditCase("grade_08", "GPA học kỳ được tính như thế nào?", "grade_policy", {"policy_retrieval", "student_grades"}, require_citation=True, require_citation_any=["Điều 32"]),
        AuditCase("grad_01", "Điều kiện xét tốt nghiệp HUIT là gì?", "graduation", {"policy_retrieval"}, require_citation=True, require_citation_any=["Điều 39"]),
        AuditCase("grad_02", "Không nộp phiếu xét tốt nghiệp thì có được xét không?", "graduation", {"policy_retrieval"}, require_citation=True, require_answer_any=["không được xét", "BM"], require_citation_any=["Điều 39"]),
        AuditCase("grad_03", "Muốn xét tốt nghiệp dùng biểu mẫu nào?", "graduation", {"procedure_or_form", "policy_retrieval"}, require_citation=True, require_answer_any=["BM12", "BM_ĐH/12"], require_citation_any=["BM12", "Điều 39"]),
        AuditCase("grad_04", "GPA 3.4 thì xếp loại tốt nghiệp gì?", "graduation", {"policy_retrieval"}, require_citation=True, require_answer_any=["Giỏi", "3,20", "3.20"], require_citation_any=["Điều 40"], require_article40_constraints=True),
        AuditCase("grad_05", "Học lại quá 5% tín chỉ thì có bị hạ bằng Giỏi không?", "graduation", {"policy_retrieval"}, require_citation=True, require_answer_all=["5%", "Giỏi"], require_citation_any=["Điều 40"], require_article40_constraints=True),
        AuditCase("grad_06", "Bị kỷ luật cảnh cáo thì xếp loại Giỏi có bị ảnh hưởng không?", "graduation", {"policy_retrieval"}, require_citation=True, require_answer_any=["cảnh cáo", "kỷ luật"], require_citation_any=["Điều 40"], require_article40_constraints=True),
        AuditCase("mixed_01", "SV002 còn nợ môn thì có được xét tốt nghiệp không?", "mixed", {"mixed_policy_student"}, require_citation=True, require_tool=True, require_answer_any=["chưa đủ", "môn nợ"], require_citation_any=["Điều 39"]),
        AuditCase("mixed_02", "Em còn nợ 2 môn thì có được xét tốt nghiệp không?", "mixed", {"mixed_policy_student"}, {"need_clarification"}, require_citation=False),
        AuditCase("mixed_03", "SV003 GPA thấp thì có được xét tốt nghiệp không?", "mixed", {"mixed_policy_student"}, require_citation=True, require_tool=True, require_answer_any=["chưa đủ", "GPA"], require_citation_any=["Điều 39"]),
        AuditCase("mixed_04", "SV004 có bị giảm xếp loại tốt nghiệp không?", "mixed", {"mixed_policy_student"}, require_citation=True, require_tool=True, require_answer_all=["5%"], require_citation_any=["Điều 40"], require_article40_constraints=True),
        AuditCase("mixed_05", "Em muốn biết mình đủ điều kiện ra trường chưa, MSSV SV005.", "mixed", {"mixed_policy_student"}, require_citation=True, require_tool=True, require_answer_any=["chưa đủ", "thiếu"], require_citation_any=["Điều 39"]),
        AuditCase("mixed_06", "SV001 có đủ điều kiện cơ bản để tốt nghiệp không?", "mixed", {"mixed_policy_student"}, require_citation=True, require_tool=True, require_answer_any=["đủ điều kiện", "có vẻ"], require_citation_any=["Điều 39"]),
        AuditCase("tool_01", "Lịch học hôm nay của SV001?", "tool", {"student_schedule"}, require_tool=True, require_answer_any=["TP101", "Lịch học"]),
        AuditCase("tool_02", "Thời khóa biểu tuần này của SV004?", "tool", {"student_schedule"}, require_tool=True, require_answer_any=["SV004", "Lịch học"]),
        AuditCase("tool_03", "Không biết mình có hỗ trợ tra cứu thời khóa biểu không ạ? MSSV của em là SV004.", "tool", {"student_schedule"}, require_tool=True, require_answer_any=["SV004", "Lịch học"]),
        AuditCase("tool_04", "GPA của SV003 bao nhiêu?", "tool", {"student_grades"}, require_tool=True, require_answer_any=["1.86", "GPA"]),
        AuditCase("tool_05", "SV002 còn nợ môn nào?", "tool", {"student_grades"}, require_tool=True, require_answer_any=["Môn", "nợ"]),
        AuditCase("tool_06", "Điểm của em thế nào? MSSV SV001.", "tool", {"student_grades"}, require_tool=True, require_answer_any=["GPA", "SV001"]),
        AuditCase("tool_07", "Lịch học hôm nay của em?", "tool_clarification", {"student_schedule"}, {"need_clarification"}, session_id="hybrid_clarify_schedule"),
        AuditCase("tool_08", "SV001", "tool_clarification", {"student_schedule"}, session_id="hybrid_clarify_schedule", require_tool=True, require_answer_any=["TP101", "Lịch học"]),
        AuditCase("form_01", "Muốn chuyển ngành dùng biểu mẫu nào?", "form", {"procedure_or_form", "policy_retrieval"}, require_citation=True, require_answer_any=["BM03"]),
        AuditCase("form_02", "BM12 dùng để làm gì?", "form", {"procedure_or_form", "policy_retrieval"}, require_citation=True, require_answer_any=["xét tốt nghiệp", "BM12"]),
        AuditCase("form_03", "BM11 nộp ở đâu?", "form", {"procedure_or_form"}, require_citation=True, require_answer_any=["BM11"], require_form_place=True),
        AuditCase("form_04", "Muốn hủy học phần dùng mẫu nào?", "form", {"procedure_or_form", "policy_retrieval"}, require_citation=True, require_answer_any=["BM10"]),
        AuditCase("form_05", "Muốn trở lại học tập dùng biểu mẫu nào?", "form", {"procedure_or_form"}, require_citation=True, require_answer_any=["BM02"]),
        AuditCase("form_06", "Muốn học cùng lúc hai chương trình dùng mẫu nào?", "form", {"procedure_or_form"}, require_citation=True, require_answer_any=["BM04"]),
        AuditCase("form_07", "Muốn chuyển hệ đào tạo dùng mẫu nào?", "form", {"procedure_or_form"}, require_citation=True, require_answer_any=["BM08"]),
        AuditCase("guide_01", "Quy trình đăng ký học phần thế nào?", "guidance", {"procedure_or_form"}, require_citation=True, require_answer_any=["đăng ký học phần"]),
        AuditCase("guide_02", "Rút học phần có thời hạn không?", "guidance", {"procedure_or_form"}, require_citation=True, require_answer_any=["rút học phần"]),
        AuditCase("guide_03", "Học cải thiện đăng ký thế nào?", "guidance", {"procedure_or_form"}, require_citation=True, require_answer_any=["cải thiện", "học lại"]),
        AuditCase("guide_04", "Đăng ký học lại làm sao?", "guidance", {"procedure_or_form"}, require_citation=True, require_answer_any=["học lại"]),
        AuditCase("guide_05", "Xem kết quả học tập ở đâu?", "guidance", {"procedure_or_form"}, require_citation=True, require_answer_any=["kết quả học tập"]),
        AuditCase("guide_06", "Phúc khảo điểm thế nào?", "guidance", {"procedure_or_form"}, require_citation=True, require_answer_any=["phúc khảo"]),
        AuditCase("guide_07", "Tạm dừng học tập cần làm gì?", "guidance", {"procedure_or_form"}, require_citation=True, require_answer_any=["tạm dừng"]),
        AuditCase("guide_08", "Chuyển ngành cần điều kiện gì?", "guidance", {"policy_retrieval", "procedure_or_form"}, require_citation=True, require_answer_any=["chuyển ngành"]),
        AuditCase("bound_01", "Học bổng HUIT xét thế nào?", "boundary", {"fallback"}, {"fallback"}, forbid_answer_any=["theo quy định chung"]),
        AuditCase("bound_02", "Học phí ngành Công nghệ thông tin bao nhiêu?", "boundary", {"fallback"}, {"fallback"}),
        AuditCase("bound_03", "QĐ-3297 còn áp dụng cho chuẩn CNTT không?", "boundary", {"fallback"}, {"fallback"}, forbid_documents=["huit_qd_3297_it_outcomes_2023"]),
        AuditCase("bound_04", "QĐ-3230 quy định chuẩn ngoại ngữ hiện tại thế nào?", "boundary", {"fallback"}, {"fallback"}, forbid_documents=["huit_qd_3230_foreign_language_outcomes_2023"], forbid_answer_any=["3230"]),
        AuditCase("bound_05", "BM09 hoãn thi còn dùng được không?", "boundary", {"fallback"}, {"fallback"}, forbid_documents=["huit_form_bm09_exam_postponement"]),
        AuditCase("bound_06", "QĐ-2658 quy định kỷ luật sinh viên thế nào?", "boundary", {"fallback"}, {"fallback"}, forbid_documents=["huit_qd_2658_student_affairs_2023"]),
        AuditCase("bound_07", "Phòng tài chính ở số điện thoại nào?", "boundary", {"fallback"}, {"fallback"}, forbid_answer_any=["090", "@"]),
        AuditCase("bound_08", "Ai là chuyên viên phụ trách ngành của em?", "boundary", {"fallback"}, {"fallback"}),
        AuditCase("natural_01", "Em muốn ra trường thì cần làm gì?", "natural", {"mixed_policy_student"}, {"need_clarification"}),
        AuditCase("natural_02", "Em học lại nhiều quá có sao không?", "natural", {"mixed_policy_student"}, {"need_clarification"}),
        AuditCase("natural_03", "Điểm em thấp thì bị cảnh báo gì không?", "natural", {"student_grades"}, {"need_clarification"}),
        AuditCase("natural_04", "Muốn biết mình còn thiếu gì để tốt nghiệp.", "natural", {"mixed_policy_student"}, {"need_clarification"}),
        AuditCase("natural_05", "Cho em hỏi về điểm chữ.", "natural", {"policy_retrieval"}, require_citation=True, require_citation_any=["Điều 30"]),
        AuditCase("natural_06", "Em muốn đổi ngành.", "natural", {"procedure_or_form", "policy_retrieval"}, require_citation=True, require_answer_any=["chuyển ngành"]),
        AuditCase("natural_07", "Em muốn xin miễn giảm/công nhận điểm.", "natural", {"procedure_or_form"}, require_citation=True, require_answer_any=["BM11", "miễn giảm"]),
        AuditCase("natural_08", "Em bị vướng lịch thi thì làm sao?", "natural", {"fallback", "policy_retrieval"}, {"fallback", "answered"}),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Stage 2B hybrid planner and guarded agent flow.")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "mock"))
    parser.add_argument("--planner-mode", default=os.environ.get("HYBRID_PLANNER_MODE", "auto"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--report-json", type=Path, default=REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=REPORT_MD)
    args = parser.parse_args()

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ["LLM_PROVIDER"] = args.provider
    os.environ.setdefault("MOCK_LLM_MODE", "template")
    os.environ["HYBRID_PLANNER_MODE"] = args.planner_mode

    selected = cases()[: args.limit] if args.limit else cases()
    started = time.time()
    results = [_run_case(case) for case in selected]
    elapsed = time.time() - started
    passed = sum(1 for item in results if item["passed"])
    report = {
        "provider": args.provider,
        "planner_mode": args.planner_mode,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "elapsed_seconds": round(elapsed, 3),
        "by_category": _by_category(results),
        "results": results,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report_md.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("provider", "planner_mode", "total", "passed", "failed", "elapsed_seconds", "by_category")}, ensure_ascii=False, indent=2))
    return 0 if passed == len(results) else 1


def _run_case(case: AuditCase) -> dict[str, Any]:
    response = run_agent(case.query, session_id=case.session_id or f"hybrid_{case.case_id}")
    data = response.to_dict()
    errors: list[str] = []
    answer = data.get("answer") or ""
    citations = data.get("citations") or []
    route = data.get("route")
    status = data.get("status")
    tool_results = data.get("tool_results") or {}
    retrieval_results = data.get("retrieval_results") or []
    planner = data.get("planner") or {}

    if route not in case.expected_routes:
        errors.append(f"route:{route}")
    if status not in case.expected_statuses:
        errors.append(f"status:{status}")
    if case.require_citation and not citations:
        errors.append("missing_citation")
    if case.require_citation_any and not any(any(token in citation for token in case.require_citation_any) for citation in citations):
        errors.append("citation_mismatch")
    if case.require_tool and not tool_results:
        errors.append("missing_tool_results")
    if case.require_planner and not planner:
        errors.append("missing_planner_meta")
    if case.require_answer_any and not any(token.lower() in answer.lower() for token in case.require_answer_any):
        errors.append("answer_missing_any:" + "|".join(case.require_answer_any))
    for token in case.require_answer_all:
        if token.lower() not in answer.lower():
            errors.append(f"answer_missing:{token}")
    for token in case.forbid_answer_any:
        if token.lower() in answer.lower():
            errors.append(f"forbidden_answer:{token}")
    docs = {item.get("document_id") for item in retrieval_results}
    for doc_id in case.forbid_documents:
        if doc_id in docs:
            errors.append(f"forbidden_document:{doc_id}")
    if case.require_article40_constraints:
        lower = answer.lower()
        if "5%" not in answer:
            errors.append("missing_article40_5_percent")
        if "kỷ luật" not in lower and "cảnh cáo" not in lower:
            errors.append("missing_article40_discipline")
    if case.require_form_place:
        lower = answer.lower()
        if "c.105" not in lower and "phòng đào tạo" not in lower:
            errors.append("missing_form_place")
    if data.get("critic", {}).get("passed") is False:
        errors.append("critic_failed:" + "|".join(data.get("critic", {}).get("errors", [])))

    return {
        "case_id": case.case_id,
        "category": case.category,
        "query": case.query,
        "passed": not errors,
        "errors": errors,
        "route": route,
        "status": status,
        "planner_mode": planner.get("mode"),
        "planner_provider": planner.get("provider"),
        "llm_provider": (data.get("llm") or {}).get("provider"),
        "citations": citations,
        "tool_present": bool(tool_results),
        "answer_preview": " ".join(answer.split())[:240],
    }


def _by_category(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for item in results:
        stats = grouped.setdefault(item["category"], {"total": 0, "passed": 0, "failed": 0})
        stats["total"] += 1
        if item["passed"]:
            stats["passed"] += 1
        else:
            stats["failed"] += 1
    return grouped


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Stage 2B Hybrid Audit",
        "",
        f"- Provider: `{report['provider']}`",
        f"- Planner mode: `{report['planner_mode']}`",
        f"- Total: `{report['total']}`",
        f"- Passed: `{report['passed']}`",
        f"- Failed: `{report['failed']}`",
        f"- Elapsed seconds: `{report['elapsed_seconds']}`",
        "",
        "## By Category",
        "",
        "| Category | Passed | Total |",
        "|---|---:|---:|",
    ]
    for category, stats in report["by_category"].items():
        lines.append(f"| `{category}` | `{stats['passed']}` | `{stats['total']}` |")
    lines.extend(["", "## Cases", "", "| Case | Category | Route | Status | Planner | LLM | Result | Errors |", "|---|---|---|---|---|---|---|---|"])
    for item in report["results"]:
        result = "PASS" if item["passed"] else "FAIL"
        errors = ", ".join(item["errors"])
        lines.append(
            f"| `{item['case_id']}` | `{item['category']}` | `{item['route']}` | `{item['status']}` | "
            f"`{item.get('planner_mode')}` | `{item.get('llm_provider')}` | `{result}` | {errors} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
