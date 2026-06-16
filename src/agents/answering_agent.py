from __future__ import annotations

from typing import Any

from .models import PlannerDecision


def answer(
    query: str,
    decision: PlannerDecision,
    retrieval_results: list[dict[str, Any]],
    tool_result: dict[str, Any],
    student_id: str | None,
) -> tuple[str, list[str]]:
    citations = _citations(retrieval_results)
    if decision.route == "policy_retrieval":
        return _policy_answer(retrieval_results), citations
    if decision.route == "procedure_or_form":
        return _procedure_answer(retrieval_results), citations
    if decision.route == "student_schedule":
        return _schedule_answer(tool_result), citations
    if decision.route == "student_grades":
        return _grades_answer(tool_result), citations
    if decision.route in {"student_graduation", "mixed_policy_student"}:
        return _graduation_answer(retrieval_results, tool_result), citations
    return ("Mình chưa xác định được luồng xử lý phù hợp cho câu hỏi này.", citations)


def _citations(results: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    citations: list[str] = []
    for item in results:
        citation = item.get("citation")
        if citation and citation not in seen:
            citations.append(citation)
            seen.add(citation)
    return citations


def _preview(text: str, limit: int = 420) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _policy_answer(results: list[dict[str, Any]]) -> str:
    if not results:
        return "Mình chưa tìm thấy căn cứ trong kho quy định đã duyệt."
    top = results[0]
    return (
        "Theo nguồn học vụ đã duyệt, nội dung liên quan nhất là: "
        f"{_preview(top.get('text', ''))}\n\n"
        f"Căn cứ: {top.get('citation')}"
    )


def _procedure_answer(results: list[dict[str, Any]]) -> str:
    if not results:
        return "Mình chưa tìm thấy hướng dẫn hoặc biểu mẫu phù hợp trong kho dữ liệu đã duyệt."
    top = results[0]
    metadata = top.get("metadata", {})
    form_code = metadata.get("form_code")
    form_name = metadata.get("form_name") or metadata.get("document_title")
    if form_code:
        place = _submission_place(top.get("text", ""))
        place_text = f"\nNơi nộp/đơn vị xử lý ghi nhận trong nguồn: {place}." if place else "\nMình chưa thấy nơi nộp rõ trong nguồn đã duyệt."
        return (
            f"Bạn dùng {form_code} - {form_name}."
            f"{place_text}\n"
            "Lưu ý: biểu mẫu chỉ hỗ trợ thủ tục; điều kiện/quy định gốc vẫn cần đối chiếu với quy chế và hướng dẫn học vụ hiện hành.\n\n"
            f"Căn cứ: {top.get('citation')}"
        )
    return (
        "Theo hướng dẫn học vụ đã duyệt: "
        f"{_preview(top.get('text', ''))}\n\n"
        f"Căn cứ: {top.get('citation')}"
    )


def _submission_place(text: str) -> str | None:
    lowered = text.lower()
    if "c.105" in lowered or "phòng đào tạo" in lowered or "phong dao tao" in lowered:
        return "Phòng Đào tạo, C.105"
    return None


def _schedule_answer(tool_result: dict[str, Any]) -> str:
    if not tool_result.get("found"):
        return "Mình không tìm thấy sinh viên này trong dữ liệu mock."
    schedule = tool_result.get("schedule", [])
    if not schedule:
        return f"Hiện dữ liệu mock chưa có lịch học cho {tool_result.get('student_id')}."
    lines = [f"Lịch học mock của {tool_result.get('student_id')}:"]
    for item in schedule:
        lines.append(
            "- {day} {time}: {course_code} - {course_name}, phòng {room}, giảng viên {lecturer}".format(**item)
        )
    return "\n".join(lines)


def _grades_answer(tool_result: dict[str, Any]) -> str:
    if not tool_result.get("found"):
        return "Mình không tìm thấy sinh viên này trong dữ liệu mock."
    failed = tool_result.get("failed_courses", [])
    lines = [
        f"Dữ liệu điểm mock của {tool_result.get('student_id')}:",
        f"- GPA tích lũy: {tool_result.get('cumulative_gpa')}",
        f"- Tổng tín chỉ tích lũy/ghi nhận: {tool_result.get('total_credits')}",
    ]
    if failed:
        lines.append("- Môn đang nợ: " + ", ".join(f"{c['course_code']} - {c['course_name']}" for c in failed))
    else:
        lines.append("- Chưa ghi nhận môn nợ trong dữ liệu mock.")
    return "\n".join(lines)


def _graduation_answer(results: list[dict[str, Any]], tool_result: dict[str, Any]) -> str:
    if not tool_result.get("found"):
        return "Mình không tìm thấy sinh viên này trong dữ liệu mock."
    policy = results[0] if results else {}
    failed = tool_result.get("failed_courses", [])
    missing = tool_result.get("missing_certificates", [])
    warnings = tool_result.get("warnings", [])
    lines = [
        "Mình đối chiếu dữ liệu cá nhân mock với quy định tốt nghiệp như sau:",
        f"- Sinh viên: {tool_result.get('student_id')} - {tool_result.get('full_name')}",
        f"- GPA tích lũy: {tool_result.get('cumulative_gpa')}",
        f"- Môn nợ: {len(failed)}",
        f"- Chứng chỉ/điều kiện còn thiếu: {', '.join(missing) if missing else 'không ghi nhận'}",
    ]
    if tool_result.get("eligible_for_graduation"):
        lines.append("Kết luận tạm thời: dữ liệu mock cho thấy sinh viên có vẻ đủ điều kiện cơ bản để xét tốt nghiệp.")
    else:
        lines.append("Kết luận tạm thời: sinh viên chưa đủ điều kiện cơ bản để xét tốt nghiệp theo dữ liệu mock.")
    if failed:
        lines.append("Lý do: còn học phần chưa đạt/chưa hoàn tất.")
    if missing:
        lines.append("Lý do: còn thiếu điều kiện chứng chỉ hoặc học phần điều kiện.")
    if "retake_ratio_over_5_percent" in warnings:
        lines.append("Cảnh báo xếp loại: tỷ lệ tín chỉ học lại vượt 5%, cần đối chiếu quy tắc giảm hạng xếp loại tốt nghiệp tại Điều 40.")
    if policy:
        lines.append(f"\nCăn cứ chính: {policy.get('citation')}")
    return "\n".join(lines)
