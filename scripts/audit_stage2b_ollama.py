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


REPORT_JSON = PROJECT_ROOT / "data" / "review" / "stage2b_ollama_audit.json"
REPORT_MD = PROJECT_ROOT / "data" / "review" / "stage2b_ollama_audit.md"


@dataclass
class AuditCase:
    id: str
    query: str
    expected_route: str
    expected_status: str = "answered"
    expected_answer_contains: list[str] = field(default_factory=list)
    expected_citation_contains: list[str] = field(default_factory=list)
    expected_student_id: str | None = None
    notes: str = ""


CASES = [
    AuditCase(
        id="policy_graduation_conditions",
        query="Điều kiện xét tốt nghiệp của sinh viên HUIT là gì?",
        expected_route="policy_retrieval",
        expected_answer_contains=["tốt nghiệp"],
        expected_citation_contains=["Điều 39"],
    ),
    AuditCase(
        id="policy_graduation_ranking_5_percent",
        query="Xếp loại tốt nghiệp có bị giảm nếu học lại quá 5% tín chỉ không?",
        expected_route="policy_retrieval",
        expected_answer_contains=["5%"],
        expected_citation_contains=["Điều 40"],
    ),
    AuditCase(
        id="policy_gpa_scale",
        query="Thang điểm đánh giá kết quả học tập học phần tại HUIT như thế nào?",
        expected_route="policy_retrieval",
        expected_answer_contains=["điểm"],
        expected_citation_contains=["Điều 30"],
    ),
    AuditCase(
        id="policy_academic_warning",
        query="Sinh viên bị cảnh báo học tập trong trường hợp nào?",
        expected_route="policy_retrieval",
        expected_answer_contains=["cảnh báo"],
        expected_citation_contains=["Điều"],
    ),
    AuditCase(
        id="policy_withdraw_course",
        query="Sinh viên muốn rút học phần thì làm thế nào?",
        expected_route="procedure_or_form",
        expected_answer_contains=["rút"],
        expected_citation_contains=["Điều 22"],
    ),
    AuditCase(
        id="form_graduation_application",
        query="Muốn xét tốt nghiệp thì dùng biểu mẫu nào?",
        expected_route="procedure_or_form",
        expected_answer_contains=["BM"],
        expected_citation_contains=["BM12"],
    ),
    AuditCase(
        id="form_credit_recognition",
        query="Muốn xét miễn giảm và công nhận điểm thì dùng phiếu nào?",
        expected_route="procedure_or_form",
        expected_answer_contains=["BM11"],
        expected_citation_contains=["BM11"],
    ),
    AuditCase(
        id="form_pause_study",
        query="Em muốn tạm dừng học thì cần biểu mẫu nào?",
        expected_route="procedure_or_form",
        expected_answer_contains=["BM"],
        expected_citation_contains=["Biểu mẫu"],
    ),
    AuditCase(
        id="tool_schedule",
        query="Lịch học hôm nay của SV001 là gì?",
        expected_route="student_schedule",
        expected_answer_contains=["07:00"],
        expected_student_id="SV001",
    ),
    AuditCase(
        id="tool_grade_gpa",
        query="GPA của SV003 bao nhiêu?",
        expected_route="student_grades",
        expected_answer_contains=["1.86"],
        expected_student_id="SV003",
    ),
    AuditCase(
        id="tool_failed_courses",
        query="SV002 còn nợ môn nào?",
        expected_route="student_grades",
        expected_answer_contains=["môn"],
        expected_student_id="SV002",
    ),
    AuditCase(
        id="mixed_failed_graduation",
        query="SV002 còn nợ môn thì có được xét tốt nghiệp không?",
        expected_route="mixed_policy_student",
        expected_answer_contains=["nợ"],
        expected_citation_contains=["Điều 39"],
        expected_student_id="SV002",
    ),
    AuditCase(
        id="mixed_low_gpa_graduation",
        query="SV003 GPA dưới 2.0 thì có được công nhận tốt nghiệp không?",
        expected_route="mixed_policy_student",
        expected_answer_contains=["1.86"],
        expected_citation_contains=["Điều 39"],
        expected_student_id="SV003",
    ),
    AuditCase(
        id="mixed_retake_ranking",
        query="SV004 học lại nhiều thì xếp loại giỏi có bị ảnh hưởng không?",
        expected_route="mixed_policy_student",
        expected_answer_contains=["5%"],
        expected_citation_contains=["Điều 40"],
        expected_student_id="SV004",
    ),
    AuditCase(
        id="mixed_missing_certificates",
        query="SV005 có được công nhận tốt nghiệp không?",
        expected_route="mixed_policy_student",
        expected_answer_contains=["thiếu"],
        expected_citation_contains=["Điều 39"],
        expected_student_id="SV005",
    ),
    AuditCase(
        id="clarification_missing_student_id_schedule",
        query="Lịch học hôm nay của em là gì?",
        expected_route="student_schedule",
        expected_status="need_clarification",
        expected_answer_contains=["MSSV"],
        notes="Clarification should not call LLM.",
    ),
    AuditCase(
        id="clarification_missing_student_id_graduation",
        query="Em còn nợ môn thì có được tốt nghiệp không?",
        expected_route="mixed_policy_student",
        expected_status="need_clarification",
        expected_answer_contains=["MSSV"],
        notes="Clarification should not call LLM.",
    ),
    AuditCase(
        id="fallback_out_of_scope",
        query="Trường bán áo hoodie ở đâu?",
        expected_route="fallback",
        expected_status="fallback",
        expected_answer_contains=["chưa đủ căn cứ"],
        notes="Out-of-scope question should not call LLM.",
    ),
]


def main() -> int:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("LLM_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:7b")
    os.environ.setdefault("LLM_TIMEOUT_SECONDS", "60")
    os.environ.setdefault("LLM_TEMPERATURE", "0.2")

    results: list[dict[str, Any]] = []
    started = time.perf_counter()
    for index, case in enumerate(CASES, start=1):
        case_started = time.perf_counter()
        response = run_agent(case.query, session_id=f"stage2b_ollama_audit_{case.id}")
        elapsed = round(time.perf_counter() - case_started, 3)
        checks = _evaluate(case, response.to_dict())
        passed = all(item["passed"] for item in checks)
        record = {
            "id": case.id,
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

    summary = {
        "provider": os.environ.get("LLM_PROVIDER"),
        "model": os.environ.get("OLLAMA_MODEL"),
        "total_cases": len(results),
        "passed_cases": sum(1 for item in results if item["passed"]),
        "failed_cases": sum(1 for item in results if not item["passed"]),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
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
    llm = response.get("llm", {})
    checks = [
        _check("status", response.get("status") == case.expected_status, f"expected {case.expected_status}, got {response.get('status')}"),
        _check("route", response.get("route") == case.expected_route, f"expected {case.expected_route}, got {response.get('route')}"),
        _check("critic_passed", response.get("critic", {}).get("passed") is True, f"critic={response.get('critic')}"),
    ]
    if case.expected_status == "answered":
        checks.append(
            _check(
                "llm_used",
                llm.get("provider") == "ollama" and llm.get("used") is True and llm.get("fallback_used") is False,
                f"llm={llm}",
            )
        )
    else:
        checks.append(_check("llm_not_required", not llm or llm.get("used") is not True, f"llm={llm}"))
    if case.expected_student_id:
        checks.append(
            _check(
                "student_id",
                response.get("student_id") == case.expected_student_id,
                f"expected {case.expected_student_id}, got {response.get('student_id')}",
            )
        )
    for expected in case.expected_answer_contains:
        checks.append(
            _check(
                f"answer_contains:{expected}",
                expected.lower() in answer.lower(),
                f"answer does not contain {expected}",
            )
        )
    citation_text = "\n".join(citations)
    for expected in case.expected_citation_contains:
        checks.append(
            _check(
                f"citation_contains:{expected}",
                expected.lower() in citation_text.lower(),
                f"citations do not contain {expected}",
            )
        )
    return checks


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": "" if passed else detail}


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Stage 2B Ollama Audit",
        "",
        f"- Provider: `{summary['provider']}`",
        f"- Model: `{summary['model']}`",
        f"- Passed: `{summary['passed_cases']}/{summary['total_cases']}`",
        f"- Failed: `{summary['failed_cases']}`",
        f"- Elapsed seconds: `{summary['elapsed_seconds']}`",
        "",
        "| Case | Status | Route | LLM | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in payload["results"]:
        response = item["response"]
        llm = response.get("llm", {})
        result = "PASS" if item["passed"] else "FAIL"
        lines.append(
            f"| `{item['id']}` | `{response.get('status')}` | `{response.get('route')}` | "
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
        for check in failed_checks:
            lines.append(f"- `{check['name']}`: {check['detail']}")
        lines.append("")
    if not failed_any:
        lines.append("Không có failed checks.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
