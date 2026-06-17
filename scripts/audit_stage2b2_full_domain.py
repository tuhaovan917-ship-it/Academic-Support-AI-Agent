from __future__ import annotations

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


REPORT_JSON = PROJECT_ROOT / "data" / "review" / "stage2b2_full_domain_audit.json"
REPORT_MD = PROJECT_ROOT / "data" / "review" / "stage2b2_full_domain_audit.md"


@dataclass
class AuditCase:
    id: str
    query: str
    expected_route: str
    expected_status: str = "answered"
    category: str = "general"
    expected_answer_contains: list[str] = field(default_factory=list)
    expected_answer_contains_any: list[str] = field(default_factory=list)
    expected_citation_contains: list[str] = field(default_factory=list)
    expected_student_id: str | None = None
    forbidden_answer_contains: list[str] = field(default_factory=list)
    require_citation: bool = False
    require_legal_granularity: bool = False
    require_article_40_constraints: bool = False
    require_form_location_c105: bool = False
    allow_deterministic: bool = True
    expected_issue_type_if_fail: str = "unknown"
    notes: str = ""


CASES: list[AuditCase] = [
    # QD-3344 policy
    AuditCase("qd3344_graduation_conditions_01", "Điều kiện xét tốt nghiệp của sinh viên HUIT là gì?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 39"], expected_answer_contains_any=["2,00", "2.00"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_graduation_conditions_02", "Điều kiện để ra trường là gì?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 39"], expected_answer_contains=["tốt nghiệp"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_graduation_bm12", "Không nộp phiếu xét tốt nghiệp thì có được xét không?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 39"], expected_answer_contains_any=["BM", "đăng ký xét tốt nghiệp"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_ranking_01", "Xếp loại tốt nghiệp Giỏi được tính thế nào?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 40"], expected_answer_contains_any=["3,20", "3.20"], require_citation=True, require_legal_granularity=True, require_article_40_constraints=True),
    AuditCase("qd3344_ranking_02", "Làm sao để đạt bằng giỏi ở HUIT?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 40"], expected_answer_contains_any=["Giỏi", "3,20", "3.20"], require_citation=True, require_legal_granularity=True, require_article_40_constraints=True),
    AuditCase("qd3344_ranking_03", "Học lại quá 5% tín chỉ có bị giảm xếp loại tốt nghiệp không?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 40"], expected_answer_contains=["5%"], require_citation=True, require_legal_granularity=True, require_article_40_constraints=True),
    AuditCase("qd3344_ranking_04", "Bị kỷ luật cảnh cáo thì bằng xuất sắc có bị hạ không?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 40"], expected_answer_contains_any=["cảnh cáo", "kỷ luật"], require_citation=True, require_legal_granularity=True, require_article_40_constraints=True),
    AuditCase("qd3344_grade_table_general", "Thang điểm đánh giá học phần tại HUIT gồm những thang nào?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 30"], expected_answer_contains_any=["thang điểm 10", "điểm chữ", "hệ 4"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_grade_conversion_68", "6.8 điểm thì quy đổi sang hệ 4 và điểm chữ thế nào?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 30"], expected_answer_contains_any=["C+", "2.5"], forbidden_answer_contains=["MSSV"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_grade_conversion_75", "Mình được 7.5 điểm thì quy đổi sang điểm hệ số 4 là bao nhiêu?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 30"], expected_answer_contains_any=["B", "3.0"], forbidden_answer_contains=["MSSV"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_grade_conversion_52", "Điểm 5,2 tương ứng điểm chữ gì?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 30"], expected_answer_contains_any=["D+", "1.5"], forbidden_answer_contains=["MSSV"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_special_i", "Điểm I là gì?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 30"], expected_answer_contains=["I"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_special_f", "Điểm F nghĩa là gì?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 30"], expected_answer_contains=["F"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_training_time", "Thời gian đào tạo tối đa của đại học chính quy cấp bằng cử nhân là bao lâu?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 18"], expected_answer_contains_any=["12", "6"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_dual_program", "Học cùng lúc hai chương trình cần điều kiện gì?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 27"], expected_answer_contains_any=["hai chương trình", "GPA"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_change_major", "Chuyển ngành trong trường cần điều kiện gì?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 25"], expected_answer_contains=["chuyển ngành"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_transfer_school", "Sinh viên muốn chuyển trường thì điều kiện thế nào?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 28"], expected_answer_contains=["chuyển trường"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_warning", "Sinh viên bị cảnh báo học tập trong trường hợp nào?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều"], expected_answer_contains=["cảnh báo"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_dismissal", "Khi nào sinh viên bị buộc thôi học?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều"], expected_answer_contains=["buộc thôi học"], require_citation=True, require_legal_granularity=True),
    AuditCase("qd3344_gpa_formula", "GPA tích lũy được tính như thế nào?", "policy_retrieval", category="qd3344", expected_citation_contains=["Điều 32"], expected_answer_contains_any=["GPA", "trung bình"], require_citation=True, require_legal_granularity=True),

    # Guidance/procedure
    AuditCase("guidance_course_registration", "Đăng ký học phần như thế nào?", "procedure_or_form", category="guidance", expected_citation_contains=["Dang ky hoc phan"], expected_answer_contains_any=["đăng ký", "học phần"], require_citation=True),
    AuditCase("guidance_retake", "Đăng ký học lại ra sao?", "procedure_or_form", category="guidance", expected_citation_contains=["Dang ky hoc phan"], expected_answer_contains=["học lại"], require_citation=True),
    AuditCase("guidance_improve", "Học cải thiện điểm có được không?", "procedure_or_form", category="guidance", expected_citation_contains=["Điều 21"], expected_answer_contains_any=["cải thiện", "học lại"], require_citation=True),
    AuditCase("guidance_withdraw", "Sinh viên muốn rút học phần thì làm thế nào?", "procedure_or_form", category="guidance", expected_citation_contains=["Rút học phần"], expected_answer_contains=["rút học phần"], require_citation=True),
    AuditCase("guidance_cancel_course", "Muốn hủy học phần thì dùng mẫu nào?", "procedure_or_form", category="guidance", expected_citation_contains=["BM10"], expected_answer_contains=["BM10"], require_citation=True),
    AuditCase("guidance_pause", "Tạm dừng học tập cần làm gì?", "procedure_or_form", category="guidance", expected_citation_contains=["Tam dung"], expected_answer_contains_any=["tạm dừng", "BM"], require_citation=True),
    AuditCase("guidance_return", "Trở lại học tập sau tạm dừng cần biểu mẫu nào?", "procedure_or_form", category="guidance", expected_citation_contains=["BM02"], expected_answer_contains=["BM02"], require_citation=True),
    AuditCase("guidance_leave_school", "Thôi học tự nguyện làm thủ tục thế nào?", "procedure_or_form", category="guidance", expected_answer_contains_any=["thôi học", "Phòng Đào tạo"], require_citation=True),
    AuditCase("guidance_appeal", "Phúc khảo điểm cần làm gì?", "procedure_or_form", category="guidance", expected_answer_contains=["phúc khảo"], require_citation=True),
    AuditCase("guidance_view_results", "Xem kết quả học tập ở đâu?", "procedure_or_form", category="guidance", expected_answer_contains_any=["kết quả học tập", "sinh viên"], require_citation=True),

    # Forms
    AuditCase("form_bm02", "Muốn trở lại học tập dùng mẫu nào?", "procedure_or_form", category="form", expected_citation_contains=["BM02"], expected_answer_contains=["BM02"], require_citation=True),
    AuditCase("form_bm03", "Muốn chuyển ngành dùng phiếu nào?", "procedure_or_form", category="form", expected_citation_contains=["BM03"], expected_answer_contains=["BM03"], require_citation=True),
    AuditCase("form_bm04", "Muốn học cùng lúc hai chương trình dùng mẫu nào?", "procedure_or_form", category="form", expected_citation_contains=["BM04"], expected_answer_contains=["BM04"], require_citation=True),
    AuditCase("form_bm08", "Muốn chuyển hệ đào tạo dùng mẫu nào?", "procedure_or_form", category="form", expected_citation_contains=["BM08"], expected_answer_contains=["BM08"], require_citation=True),
    AuditCase("form_bm10", "Muốn hủy học phần dùng biểu mẫu nào?", "procedure_or_form", category="form", expected_citation_contains=["BM10"], expected_answer_contains=["BM10"], require_citation=True),
    AuditCase("form_bm11", "Muốn xét miễn giảm và công nhận điểm thì dùng phiếu nào, nộp ở đâu?", "procedure_or_form", category="form", expected_citation_contains=["BM11"], expected_answer_contains=["BM11"], require_citation=True, require_form_location_c105=True),
    AuditCase("form_bm12", "Muốn xét tốt nghiệp thì dùng biểu mẫu nào?", "procedure_or_form", category="form", expected_citation_contains=["BM12"], expected_answer_contains_any=["BM12", "BM_ĐH/12"], require_citation=True),

    # Mixed/tool
    AuditCase("mixed_sv001", "SV001 có đủ điều kiện tốt nghiệp không?", "mixed_policy_student", category="mixed", expected_student_id="SV001", expected_citation_contains=["Điều 39"], expected_answer_contains_any=["đủ", "có vẻ"], require_citation=True, require_legal_granularity=True),
    AuditCase("mixed_sv002_failed", "SV002 còn nợ môn thì có được xét tốt nghiệp không?", "mixed_policy_student", category="mixed", expected_student_id="SV002", expected_citation_contains=["Điều 39"], expected_answer_contains_any=["nợ", "chưa"], require_citation=True, require_legal_granularity=True, forbidden_answer_contains=["truy cứu trách nhiệm hình sự"]),
    AuditCase("mixed_sv003_low_gpa", "SV003 GPA dưới 2.0 thì có được công nhận tốt nghiệp không?", "mixed_policy_student", category="mixed", expected_student_id="SV003", expected_citation_contains=["Điều 39"], expected_answer_contains_any=["1.86", "2,00", "2.00"], require_citation=True, require_legal_granularity=True),
    AuditCase("mixed_sv004_retake", "SV004 học lại nhiều thì xếp loại giỏi có bị ảnh hưởng không?", "mixed_policy_student", category="mixed", expected_student_id="SV004", expected_citation_contains=["Điều 40"], expected_answer_contains=["5%"], require_citation=True, require_legal_granularity=True, require_article_40_constraints=True),
    AuditCase("mixed_sv005_missing_cert", "SV005 thiếu chứng chỉ thì có được tốt nghiệp không?", "mixed_policy_student", category="mixed", expected_student_id="SV005", expected_citation_contains=["Điều 39"], expected_answer_contains_any=["thiếu", "chứng chỉ"], require_citation=True, require_legal_granularity=True),
    AuditCase("tool_gpa_sv003", "GPA của SV003 là bao nhiêu?", "student_grades", category="tool", expected_student_id="SV003", expected_answer_contains=["1.86"]),
    AuditCase("tool_schedule_sv001", "Lịch học hôm nay của SV001 là gì?", "student_schedule", category="tool", expected_student_id="SV001", expected_answer_contains_any=["07:00", "TP101"]),
    AuditCase("tool_failed_sv002", "SV002 còn nợ môn nào?", "student_grades", category="tool", expected_student_id="SV002", expected_answer_contains_any=["môn", "nợ"]),
    AuditCase("clarify_schedule", "Lịch học hôm nay của em là gì?", "student_schedule", "need_clarification", category="tool", expected_answer_contains=["MSSV"]),
    AuditCase("clarify_graduation", "Em còn nợ môn thì có được tốt nghiệp không?", "mixed_policy_student", "need_clarification", category="mixed", expected_answer_contains=["MSSV"]),

    # Knowledge boundary
    AuditCase("boundary_finance", "Để hỗ trợ các vấn đề về tài chính, mình phải liên hệ phòng nào?", "fallback", "fallback", category="boundary", expected_answer_contains_any=["chưa đủ căn cứ", "missing_data"], forbidden_answer_contains=["Phòng Tài chính"]),
    AuditCase("boundary_scholarship", "Điều kiện nhận học bổng của trường là gì?", "fallback", "fallback", category="boundary", expected_answer_contains_any=["chưa đủ căn cứ", "missing"], forbidden_answer_contains=["chắc chắn"]),
    AuditCase("boundary_bm09", "Hoãn thi cuối kỳ dùng BM09 được không?", "fallback", "fallback", category="boundary", expected_answer_contains_any=["BM09", "pending", "chưa đủ căn cứ"]),
    AuditCase("boundary_foreign_language_3230", "Chuẩn đầu ra ngoại ngữ theo QĐ-3230 hiện còn áp dụng không?", "fallback", "fallback", category="boundary", expected_answer_contains_any=["chưa đủ căn cứ", "blocked", "discarded"]),
    AuditCase("boundary_it_3297_current", "Chuẩn CNTT theo QĐ-3297 hiện còn áp dụng không?", "fallback", "fallback", category="boundary", expected_answer_contains_any=["chưa đủ căn cứ", "blocked", "pending"]),
    AuditCase("boundary_qd2658_discipline", "Quy chế công tác sinh viên QĐ-2658 quy định kỷ luật thế nào?", "fallback", "fallback", category="boundary", expected_answer_contains_any=["chưa đủ căn cứ", "pending"]),
    AuditCase("boundary_out_of_scope", "Trường bán áo hoodie ở đâu?", "fallback", "fallback", category="boundary", expected_answer_contains=["chưa đủ căn cứ"]),
]


def main() -> int:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("LLM_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:7b")
    os.environ.setdefault("LLM_TIMEOUT_SECONDS", "90")
    os.environ.setdefault("LLM_TEMPERATURE", "0.2")

    results: list[dict[str, Any]] = []
    started = time.perf_counter()
    for index, case in enumerate(CASES, start=1):
        case_started = time.perf_counter()
        response = run_agent(case.query, session_id=f"stage2b2_{case.id}")
        elapsed = round(time.perf_counter() - case_started, 3)
        checks = _evaluate(case, response.to_dict())
        passed = all(item["passed"] for item in checks)
        record = {
            "id": case.id,
            "category": case.category,
            "query": case.query,
            "passed": passed,
            "elapsed_seconds": elapsed,
            "checks": checks,
            "notes": case.notes,
            "response": response.to_dict(),
        }
        results.append(record)
        marker = "PASS" if passed else "FAIL"
        llm = record["response"].get("llm", {})
        print(
            f"[{index:02d}/{len(CASES)}] {marker} {case.id} "
            f"route={response.route} status={response.status} "
            f"llm={llm.get('provider', 'none')} fallback={llm.get('fallback_used')} "
            f"{elapsed}s"
        )

    summary = _summary(results, started)
    payload = {"summary": summary, "results": results}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(payload), encoding="utf-8")
    print(f"\nWrote {REPORT_JSON}")
    print(f"Wrote {REPORT_MD}")
    return 0 if summary["failed_cases"] == 0 else 1


def _evaluate(case: AuditCase, response: dict[str, Any]) -> list[dict[str, Any]]:
    answer = response.get("answer", "")
    citations = response.get("citations", [])
    citation_text = "\n".join(citations)
    llm = response.get("llm", {})
    checks = [
        _check("status", response.get("status") == case.expected_status, f"expected {case.expected_status}, got {response.get('status')}", "routing_error"),
        _check("route", response.get("route") == case.expected_route, f"expected {case.expected_route}, got {response.get('route')}", "routing_error"),
        _check("critic_passed", response.get("critic", {}).get("passed") is True, f"critic={response.get('critic')}", "critic_gap"),
    ]
    if case.expected_status == "answered":
        provider_ok = llm.get("provider") == "ollama" and llm.get("used") is True and llm.get("fallback_used") is False
        deterministic_ok = case.allow_deterministic and llm.get("provider") == "deterministic"
        template_fallback_ok = llm.get("provider") == "template" and response.get("critic", {}).get("passed") is True
        checks.append(_check("answer_generation", provider_ok or deterministic_ok or template_fallback_ok, f"llm={llm}", "llm_grounding_error"))
    else:
        checks.append(_check("knowledge_boundary", response.get("status") == "fallback" or not llm, f"llm={llm}", "missing_data"))
    if case.expected_student_id:
        checks.append(_check("student_id", response.get("student_id") == case.expected_student_id, f"expected {case.expected_student_id}, got {response.get('student_id')}", "tool_error"))
    if case.require_citation:
        checks.append(_check("has_citation", bool(citations), "missing citations", "retrieval_error"))
    if case.require_legal_granularity:
        checks.append(_check("citation_granularity", _has_legal_granularity(citations), f"citations={citations}", "citation_granularity"))
    for expected in case.expected_answer_contains:
        checks.append(_check(f"answer_contains:{expected}", expected.lower() in answer.lower(), f"answer does not contain {expected}", "llm_grounding_error"))
    if case.expected_answer_contains_any:
        checks.append(
            _check(
                "answer_contains_any",
                any(expected.lower() in answer.lower() for expected in case.expected_answer_contains_any),
                f"answer contains none of {case.expected_answer_contains_any}",
                "llm_grounding_error",
            )
        )
    for forbidden in case.forbidden_answer_contains:
        checks.append(_check(f"forbidden:{forbidden}", forbidden.lower() not in answer.lower(), f"answer contains forbidden term {forbidden}", "llm_grounding_error"))
    for expected in case.expected_citation_contains:
        checks.append(_check(f"citation_contains:{expected}", expected.lower() in citation_text.lower(), f"citations do not contain {expected}", "retrieval_error"))
    if case.require_article_40_constraints:
        lower = answer.lower()
        checks.append(_check("article_40_has_5_percent", "5%" in answer, "answer missed 5% retake constraint", "constraint_mapping"))
        checks.append(
            _check(
                "article_40_has_discipline_constraint",
                "kỷ luật" in lower or "cảnh cáo" in lower,
                "answer missed discipline/cảnh cáo constraint",
                "constraint_mapping",
            )
        )
    if case.require_form_location_c105:
        lower = answer.lower()
        checks.append(
            _check(
                "form_location_c105",
                "c.105" in lower or "phòng đào tạo" in lower,
                "answer missed Phòng Đào tạo/C.105 location",
                "form_metadata",
            )
        )
    return checks


def _has_legal_granularity(citations: list[str]) -> bool:
    return any("Điều" in citation for citation in citations)


def _check(name: str, passed: bool, detail: str, issue_type: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": "" if passed else detail, "issue_type": issue_type}


def _summary(results: list[dict[str, Any]], started: float) -> dict[str, Any]:
    failed = [item for item in results if not item["passed"]]
    by_category: dict[str, dict[str, int]] = {}
    issue_counts: dict[str, int] = {}
    for item in results:
        bucket = by_category.setdefault(item["category"], {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        bucket["passed" if item["passed"] else "failed"] += 1
        for check in item["checks"]:
            if not check["passed"]:
                issue_counts[check["issue_type"]] = issue_counts.get(check["issue_type"], 0) + 1
    return {
        "provider": os.environ.get("LLM_PROVIDER"),
        "model": os.environ.get("OLLAMA_MODEL"),
        "total_cases": len(results),
        "passed_cases": len(results) - len(failed),
        "failed_cases": len(failed),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "by_category": by_category,
        "issue_counts": issue_counts,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Stage 2B.2 Full Domain Audit",
        "",
        f"- Provider: `{summary['provider']}`",
        f"- Model: `{summary['model']}`",
        f"- Passed: `{summary['passed_cases']}/{summary['total_cases']}`",
        f"- Failed: `{summary['failed_cases']}`",
        f"- Elapsed seconds: `{summary['elapsed_seconds']}`",
        "",
        "## By Category",
        "",
        "| Category | Passed | Total |",
        "| --- | ---: | ---: |",
    ]
    for category, counts in sorted(summary["by_category"].items()):
        lines.append(f"| `{category}` | {counts['passed']} | {counts['total']} |")
    lines.extend(["", "## Issue Counts", ""])
    if summary["issue_counts"]:
        for issue_type, count in sorted(summary["issue_counts"].items()):
            lines.append(f"- `{issue_type}`: {count}")
    else:
        lines.append("Không có failed checks.")
    lines.extend(["", "## Cases", "", "| Case | Category | Status | Route | LLM | Result |", "| --- | --- | --- | --- | --- | --- |"])
    for item in payload["results"]:
        response = item["response"]
        llm = response.get("llm", {})
        result = "PASS" if item["passed"] else "FAIL"
        lines.append(
            f"| `{item['id']}` | `{item['category']}` | `{response.get('status')}` | `{response.get('route')}` | "
            f"`{llm.get('provider', 'none')}` | `{result}` |"
        )
    lines.extend(["", "## Failed Checks", ""])
    failed_any = False
    for item in payload["results"]:
        failed_checks = [check for check in item["checks"] if not check["passed"]]
        if not failed_checks:
            continue
        failed_any = True
        lines.append(f"### {item['id']}")
        lines.append(f"- Query: {item['query']}")
        for check in failed_checks:
            lines.append(f"- `{check['name']}` (`{check['issue_type']}`): {check['detail']}")
        lines.append("")
    if not failed_any:
        lines.append("Không có failed checks.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
