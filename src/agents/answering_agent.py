from __future__ import annotations

import re
from typing import Any

from src.llm import LLMError, get_llm_client

from .models import PlannerDecision


def answer(
    query: str,
    decision: PlannerDecision,
    retrieval_results: list[dict[str, Any]],
    tool_result: dict[str, Any],
    student_id: str | None,
) -> tuple[str, list[str], dict[str, Any]]:
    citations = _citations(retrieval_results)
    template_text = _template_answer(decision, retrieval_results, tool_result)
    deterministic = _deterministic_answer(query, decision, retrieval_results, citations)
    if deterministic:
        return deterministic
    if decision.route in {"student_schedule", "student_grades", "mixed_policy_student"}:
        return (
            template_text,
            citations,
            {
                "provider": "template",
                "used": False,
                "fallback_used": False,
                "reason": "guarded_tool_or_mixed_route",
            },
        )
    payload = _llm_payload(
        query=query,
        decision=decision,
        retrieval_results=retrieval_results,
        tool_result=tool_result,
        student_id=student_id,
        template_answer=template_text,
        citations=citations,
    )
    try:
        client = get_llm_client()
        llm_response = client.generate_answer(payload)
        _validate_llm_response(llm_response.answer, llm_response.used_citations, citations, decision)
        answer_citations = _merge_required_citations(decision, llm_response.used_citations or citations, citations)
        answer_text = _ensure_required_citation_text(llm_response.answer, decision, answer_citations)
        answer_text = _ensure_article_40_constraints(answer_text, decision, answer_citations)
        return (
            answer_text,
            answer_citations,
            {
                "provider": client.provider_name,
                "used": True,
                "fallback_used": False,
                "safety_notes": llm_response.safety_notes,
                "missing_information": llm_response.missing_information,
                "raw": llm_response.raw,
            },
        )
    except LLMError as exc:
        return (
            template_text,
            citations,
            {
                "provider": "template",
                "used": False,
                "fallback_used": True,
                "error": str(exc),
            },
        )


def template_answer(
    decision: PlannerDecision,
    retrieval_results: list[dict[str, Any]],
    tool_result: dict[str, Any],
) -> tuple[str, list[str], dict[str, Any]]:
    citations = _citations(retrieval_results)
    return (
        _template_answer(decision, retrieval_results, tool_result),
        citations,
        {
            "provider": "template",
            "used": False,
            "fallback_used": True,
            "error": "critic_rejected_llm_answer",
        },
    )


def _template_answer(
    decision: PlannerDecision,
    retrieval_results: list[dict[str, Any]],
    tool_result: dict[str, Any],
) -> str:
    if decision.route == "policy_retrieval":
        return _policy_answer(retrieval_results)
    if decision.route == "procedure_or_form":
        return _procedure_answer(retrieval_results)
    if decision.route == "student_schedule":
        return _schedule_answer(tool_result)
    if decision.route == "student_grades":
        return _grades_answer(tool_result)
    if decision.route in {"student_graduation", "mixed_policy_student"}:
        return _graduation_answer(retrieval_results, tool_result)
    return "Mình chưa xác định được luồng xử lý phù hợp cho câu hỏi này."


def _deterministic_answer(
    query: str,
    decision: PlannerDecision,
    retrieval_results: list[dict[str, Any]],
    citations: list[str],
) -> tuple[str, list[str], dict[str, Any]] | None:
    if decision.intent != "grade_conversion":
        if decision.intent == "training_time":
            return _deterministic_training_time_answer(query, citations)
        if decision.intent == "special_grade_symbol":
            return _deterministic_special_grade_answer(query, citations)
        if decision.intent == "grade_rounding":
            return _deterministic_rounding_answer(citations)
        return None
    article_30_citation = next((citation for citation in citations if "Điều 30" in citation), citations[0] if citations else "")
    letter_band = _extract_letter_band(query)
    if letter_band and _asks_letter_threshold(query):
        band = _letter_band(letter_band)
        if not band:
            return None
        answer_text = (
            f"Theo bảng quy đổi thang điểm tại Điều 30, điểm chữ {letter_band} tương ứng với "
            f"khoảng điểm hệ 10 từ {band['min_10']} đến {band['max_10']}, và điểm hệ 4 là {band['scale_4']}. "
            f"Mức xếp loại học phần tương ứng: {band['classification']}.\n\n"
            f"Căn cứ: {article_30_citation}"
        )
        return (
            answer_text,
            [article_30_citation] if article_30_citation else citations,
            {
                "provider": "deterministic",
                "used": False,
                "fallback_used": False,
                "intent": "grade_conversion",
            },
        )
    score = _extract_score(query)
    if score is None:
        return None
    converted = _convert_score_10_to_4(score)
    if converted is None:
        answer_text = (
            f"Mình nhận thấy bạn hỏi quy đổi điểm {score:g}, nhưng điểm hệ 10 hợp lệ thường nằm trong khoảng 0 đến 10. "
            "Bạn kiểm tra lại điểm cần quy đổi giúp mình nhé."
        )
    else:
        answer_text = (
            f"Với điểm hệ 10 là {score:g}, theo bảng quy đổi thang điểm tại Điều 30, "
            f"kết quả tương ứng là điểm chữ {converted['letter']} và điểm hệ 4 là {converted['scale_4']}. "
            f"Mức xếp loại học phần tương ứng: {converted['classification']}.\n\n"
            f"Căn cứ: {article_30_citation}"
        )
    return (
        answer_text,
        [article_30_citation] if article_30_citation else citations,
        {
            "provider": "deterministic",
            "used": False,
            "fallback_used": False,
            "intent": "grade_conversion",
        },
    )


def _extract_score(query: str) -> float | None:
    matches = re.findall(r"\b\d{1,2}(?:[.,]\d+)?\b", query)
    for raw in matches:
        value = float(raw.replace(",", "."))
        if 0 <= value <= 10:
            return value
    return None


def _extract_letter_band(query: str) -> str | None:
    query_lower = query.lower()
    if "b+" in query_lower:
        return "B+"
    if "c+" in query_lower:
        return "C+"
    if "d+" in query_lower:
        return "D+"
    match = re.search(r"\bđiểm\s*(a|b|c|d|f)\b", query, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\bdiem\s*(a|b|c|d|f)\b", query, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\b(a|b|c|d|f)\b", query, flags=re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).upper()
    return value[0] + "+" if value.endswith("+") else value


def _asks_letter_threshold(query: str) -> bool:
    normalized = query.lower()
    return any(term in normalized for term in ("bao nhiêu", "bao nhieu", "từ mấy", "tu may", "mấy điểm", "may diem", "mới được", "moi duoc"))


def _ensure_article_40_constraints(answer_text: str, decision: PlannerDecision, citations: list[str]) -> str:
    uses_article_40 = any("Điều 40" in citation for citation in citations)
    if not uses_article_40:
        return answer_text
    if decision.intent not in {"graduation_ranking", "mixed_graduation"}:
        return answer_text
    lower = answer_text.lower()
    missing_5_percent = "5%" not in answer_text
    missing_discipline = "kỷ luật" not in lower and "cảnh cáo" not in lower
    if not (missing_5_percent or missing_discipline):
        return answer_text
    addition = (
        "Lưu ý theo Điều 40: hạng tốt nghiệp loại Xuất sắc hoặc Giỏi sẽ bị giảm một mức nếu "
        "số tín chỉ học lại vượt quá 5% tổng số tín chỉ của chương trình hoặc người học bị kỷ luật "
        "từ mức cảnh cáo ở cấp trường trở lên."
    )
    return answer_text.rstrip() + "\n\n" + addition


def _merge_required_citations(decision: PlannerDecision, used_citations: list[str], all_citations: list[str]) -> list[str]:
    merged = list(used_citations)
    required_article = None
    if decision.route == "mixed_policy_student" and decision.intent == "mixed_graduation":
        required_article = "Điều 40" if any("Điều 40" in citation for citation in used_citations) else "Điều 39"
    if decision.intent == "graduation_conditions":
        required_article = "Điều 39"
    if decision.intent == "graduation_ranking":
        required_article = "Điều 40"
    if required_article:
        for citation in all_citations:
            if required_article in citation and citation not in merged:
                merged.insert(0, citation)
                break
    return merged


def _ensure_required_citation_text(answer_text: str, decision: PlannerDecision, citations: list[str]) -> str:
    if decision.route != "mixed_policy_student":
        return answer_text
    if any("Điều 39" in citation for citation in citations) and "Điều 39" not in answer_text:
        return answer_text.rstrip() + "\n\nCăn cứ điều kiện xét tốt nghiệp: " + next(c for c in citations if "Điều 39" in c)
    return answer_text


def _deterministic_training_time_answer(
    query: str,
    citations: list[str],
) -> tuple[str, list[str], dict[str, Any]] | None:
    normalized = query.lower()
    article_18_citation = next((citation for citation in citations if "Điều 18" in citation), citations[0] if citations else "")
    if "đại học chính quy" not in normalized and "dai hoc chinh quy" not in normalized:
        return None
    if "cử nhân" in normalized or "cu nhan" in normalized:
        answer_text = (
            "Đối với đại học chính quy cấp bằng cử nhân, thời gian theo thiết kế là 7 học kỳ/3,5 năm; "
            "thời gian tối đa là 12 học kỳ/6 năm.\n\n"
            f"Căn cứ: {article_18_citation}"
        )
    elif "kỹ sư" in normalized or "ky su" in normalized:
        answer_text = (
            "Đối với đại học chính quy cấp bằng kỹ sư, thời gian theo thiết kế là 8 học kỳ/4 năm; "
            "thời gian tối đa là 14 học kỳ/7 năm.\n\n"
            f"Căn cứ: {article_18_citation}"
        )
    else:
        return None
    return (
        answer_text,
        [article_18_citation] if article_18_citation else citations,
        {
            "provider": "deterministic",
            "used": False,
            "fallback_used": False,
            "intent": "training_time",
        },
    )


def _deterministic_special_grade_answer(
    query: str,
    citations: list[str],
) -> tuple[str, list[str], dict[str, Any]] | None:
    symbol = _extract_special_grade_symbol(query)
    if not symbol:
        return None
    info = {
        "F": "Điểm F được tính như điểm 0 trong các trường hợp như cấm thi hoặc vắng thi không phép.",
        "I": "Điểm I là điểm chưa hoàn tất, tính chưa tích lũy; nếu quá thời hạn xử lý theo quy định mà chưa có điểm đánh giá học phần thì điểm I có thể chuyển thành điểm 0.",
        "RT": "Điểm RT là rút học phần và không tính điểm.",
        "MT": "Điểm MT là điểm miễn thi/điểm thưởng, ghi chú tạm trong bảng điểm học kỳ; điểm miễn hệ 10 do Khoa đề nghị khi hoàn tất thủ tục.",
        "Z": "Điểm Z là chưa nhận điểm thi, ghi chú tạm và tính chưa tích lũy.",
        "X": "Điểm X là bảo lưu, được ghi trong mục bảo lưu và không tính vào điểm trung bình học kỳ.",
        "H": "Điểm H là hủy học phần, học phần được xóa khỏi dữ liệu điểm.",
    }.get(symbol)
    if not info:
        return None
    article_30_citation = next((citation for citation in citations if "Điều 30" in citation), citations[0] if citations else "")
    answer_text = f"{info}\n\nCăn cứ: {article_30_citation}"
    return (
        answer_text,
        [article_30_citation] if article_30_citation else citations,
        {
            "provider": "deterministic",
            "used": False,
            "fallback_used": False,
            "intent": "special_grade_symbol",
        },
    )


def _deterministic_rounding_answer(citations: list[str]) -> tuple[str, list[str], dict[str, Any]]:
    article_30_citation = next((citation for citation in citations if "Điều 30" in citation), citations[0] if citations else "")
    answer_text = (
        "Theo Điều 30, điểm ghi trong bảng điểm tính theo thang điểm 10 và được làm tròn đến một chữ số thập phân. "
        "Điểm học phần cũng là một con số đã làm tròn đến một chữ số thập phân của các cột điểm chính thức.\n\n"
        f"Căn cứ: {article_30_citation}"
    )
    return (
        answer_text,
        [article_30_citation] if article_30_citation else citations,
        {
            "provider": "deterministic",
            "used": False,
            "fallback_used": False,
            "intent": "grade_rounding",
        },
    )


def _extract_special_grade_symbol(query: str) -> str | None:
    normalized = query.upper()
    for symbol in ("RT", "MT", "CT", "I", "F", "Z", "X", "H"):
        if re.search(rf"\b{symbol}\b", normalized):
            return "F" if symbol == "CT" else symbol
    return None


def _convert_score_10_to_4(score: float) -> dict[str, Any] | None:
    if not 0 <= score <= 10:
        return None
    bands = [
        (8.5, 10.0, "A", "4.0", "Giỏi"),
        (8.0, 8.4, "B+", "3.5", "Khá"),
        (7.0, 7.9, "B", "3.0", "Khá"),
        (6.5, 6.9, "C+", "2.5", "Trung bình"),
        (5.5, 6.4, "C", "2.0", "Trung bình"),
        (5.0, 5.4, "D+", "1.5", "Trung bình yếu"),
        (4.0, 4.9, "D", "1.0", "Trung bình yếu"),
        (0.0, 3.9, "F", "0.0", "Kém"),
    ]
    rounded = round(score, 1)
    for low, high, letter, scale_4, classification in bands:
        if low <= rounded <= high:
            return {"letter": letter, "scale_4": scale_4, "classification": classification}
    return None


def _letter_band(letter: str) -> dict[str, Any] | None:
    bands = {
        "A": {"min_10": "8.5", "max_10": "10.0", "scale_4": "4.0", "classification": "Giỏi"},
        "B+": {"min_10": "8.0", "max_10": "8.4", "scale_4": "3.5", "classification": "Khá"},
        "B": {"min_10": "7.0", "max_10": "7.9", "scale_4": "3.0", "classification": "Khá"},
        "C+": {"min_10": "6.5", "max_10": "6.9", "scale_4": "2.5", "classification": "Trung bình"},
        "C": {"min_10": "5.5", "max_10": "6.4", "scale_4": "2.0", "classification": "Trung bình"},
        "D+": {"min_10": "5.0", "max_10": "5.4", "scale_4": "1.5", "classification": "Trung bình yếu"},
        "D": {"min_10": "4.0", "max_10": "4.9", "scale_4": "1.0", "classification": "Trung bình yếu"},
        "F": {"min_10": "0.0", "max_10": "3.9", "scale_4": "0.0", "classification": "Kém"},
    }
    return bands.get(letter.upper())


def _citations(results: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    citations: list[str] = []
    for item in results:
        citation = item.get("citation")
        if citation and citation not in seen:
            citations.append(citation)
            seen.add(citation)
    return citations


def _llm_payload(
    *,
    query: str,
    decision: PlannerDecision,
    retrieval_results: list[dict[str, Any]],
    tool_result: dict[str, Any],
    student_id: str | None,
    template_answer: str,
    citations: list[str],
) -> dict[str, Any]:
    return {
        "query": query,
        "route": decision.route,
        "student_id": student_id,
        "allowed_citations": citations,
        "evidence": [_evidence_item(item) for item in retrieval_results],
        "tool_results": tool_result,
        "template_answer": template_answer,
        "template_citations": citations,
    }


def _evidence_item(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata", {})
    return {
        "chunk_id": item.get("chunk_id"),
        "document_id": item.get("document_id") or metadata.get("document_id"),
        "source_type": item.get("source_type") or metadata.get("source_type"),
        "form_code": item.get("form_code") or metadata.get("form_code"),
        "form_name": metadata.get("form_name"),
        "document_title": metadata.get("document_title"),
        "unit": item.get("article_number") or metadata.get("unit_key") or metadata.get("article_number"),
        "citation": item.get("citation"),
        "text": _preview(item.get("text", ""), limit=1200),
    }


def _validate_llm_response(
    answer_text: str,
    used_citations: list[str],
    allowed_citations: list[str],
    decision: PlannerDecision,
) -> None:
    if not answer_text.strip():
        raise LLMError("empty_llm_answer")
    invalid = [citation for citation in used_citations if citation not in allowed_citations]
    if invalid:
        raise LLMError("invalid_llm_citation:" + "|".join(invalid))
    if decision.needs_retrieval and allowed_citations and not used_citations:
        raise LLMError("llm_missing_required_citation")


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
        place_text = (
            f"\nNơi nộp/đơn vị xử lý ghi nhận trong nguồn: {place}."
            if place
            else "\nMình chưa thấy nơi nộp rõ trong nguồn đã duyệt."
        )
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
    if any("Điều 40" in str(item.get("citation", "")) for item in results):
        lines.append(
            "Lưu ý Điều 40: hạng tốt nghiệp loại Xuất sắc hoặc Giỏi còn có thể bị giảm một mức nếu số tín chỉ học lại vượt quá 5% "
            "tổng số tín chỉ của chương trình hoặc người học bị kỷ luật từ mức cảnh cáo ở cấp trường trở lên."
        )
    if policy:
        lines.append(f"\nCăn cứ chính: {policy.get('citation')}")
    return "\n".join(lines)
