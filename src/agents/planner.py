from __future__ import annotations

import re
import unicodedata

from .models import PlannerDecision


STUDENT_ID_RE = re.compile(r"\bSV\d{3,6}\b|\b\d{3}\b", re.IGNORECASE)


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("đ", "d").replace("Đ", "D")
    text = re.sub(r"[^a-zA-Z0-9%.,]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def extract_student_id(query: str) -> str | None:
    match = STUDENT_ID_RE.search(query or "")
    if not match:
        return None
    raw = match.group(0).upper()
    return raw if raw.startswith("SV") else f"SV{raw}"


def plan(query: str, student_id: str | None = None, pending_route: str | None = None) -> PlannerDecision:
    normalized = normalize_text(query)
    has_student_id = bool(student_id)

    if pending_route and has_student_id and len(normalized.split()) <= 3:
        return _decision_for_pending_route(pending_route, has_student_id=True)

    if _asks_missing_finance_or_contact(normalized):
        return PlannerDecision(
            route="fallback",
            intent="missing_data_department_contact",
            notes=["missing_data:finance_or_department_contact"],
        )
    if _asks_pending_or_discarded_current_source(normalized):
        return PlannerDecision(
            route="fallback",
            intent="blocked_pending_or_discarded_current_source",
            notes=["missing_or_blocked_source:pending_or_discarded"],
        )

    if _asks_schedule(normalized):
        return _tool_decision("student_schedule", "get_student_schedule", has_student_id)

    if _asks_grade_conversion(normalized):
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 30 Bảng 3 quy đổi thang điểm 10 thang điểm 4 điểm chữ",
            intent="grade_conversion",
        )
    if _asks_rounding_policy(normalized):
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 30 Khoản 2 Khoản 3 điểm học phần làm tròn một chữ số thập phân",
            intent="grade_rounding",
        )

    if _asks_training_time(normalized):
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 18 thời gian đào tạo tối đa đại học chính quy cử nhân kỹ sư",
            intent="training_time",
        )
    if _asks_gpa_formula(normalized):
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 32 cách tính điểm trung bình học kỳ điểm trung bình tích lũy GPA",
            intent="gpa_formula",
        )
    if _asks_special_grade_policy(normalized):
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 30 Bảng 4 điểm I điểm F điểm R điểm đặc biệt kết quả học tập",
            intent="special_grade_symbol",
        )
    if _asks_change_major_condition(normalized):
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 25 điều kiện chuyển ngành đào tạo trong Trường",
            intent="change_major_conditions",
        )
    if _asks_graduation_registration_requirement(normalized):
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 39 Khoản 1 Phiếu đăng ký xét tốt nghiệp BM12 không nộp không được xét",
            intent="graduation_conditions",
        )

    if _asks_graduation_ranking(normalized) and not _is_personal_graduation_query(normalized, has_student_id):
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 40 cách tính điểm và xếp loại tốt nghiệp học lại quá 5% kỷ luật cảnh cáo",
            intent="graduation_ranking",
        )

    asks_form = any(
        term in normalized
        for term in (
            "bieu mau",
            "phieu",
            "mau nao",
            "don nao",
            "dung mau",
            "dung phieu",
            "bm02",
            "bm03",
            "bm04",
            "bm08",
            "bm10",
            "bm11",
            "bm12",
        )
    )
    asks_procedure = any(
        term in normalized
        for term in (
            "quy trinh",
            "thu tuc",
            "lam the nao",
            "nop o dau",
            "rut hoc phan",
            "huy hoc phan",
            "dang ky hoc phan",
            "dang ky hoc lai",
            "hoc cai thien",
            "cai thien",
            "phuc khao",
            "xem ket qua hoc tap",
            "ket qua hoc tap o dau",
            "chuyen nganh",
            "doi nganh",
            "tam dung",
            "tam ngung",
            "tro lai hoc",
            "mien giam",
            "cong nhan diem",
        )
    )
    if asks_form or asks_procedure:
        return PlannerDecision(
            route="procedure_or_form",
            needs_retrieval=True,
            retrieval_intent="procedure",
            retrieval_query=_procedure_retrieval_query(normalized, query),
            intent="procedure_or_form",
        )

    asks_grade = any(term in normalized for term in ("gpa", "diem", "mon no", "rot mon", "no mon", "ket qua hoc tap"))
    asks_graduation = any(term in normalized for term in ("tot nghiep", "xet tot nghiep", "cong nhan tot nghiep", "ra truong"))
    if (asks_graduation or _asks_graduation_ranking(normalized)) and _is_personal_graduation_query(normalized, has_student_id):
        return _mixed_decision(has_student_id, normalized)

    if asks_grade:
        return _tool_decision("student_grades", "get_student_grades", has_student_id)

    asks_policy = any(
        term in normalized
        for term in (
            "quy dinh",
            "dieu kien",
            "canh bao",
            "buoc thoi hoc",
            "xep loai",
            "tin chi",
            "hoc lai",
            "diem i",
            "phuc khao",
            "qd 3344",
        )
    )
    if asks_graduation:
        return PlannerDecision(
            route="policy_retrieval",
            needs_retrieval=True,
            retrieval_intent="current_policy",
            retrieval_query="Điều 39 điều kiện xét tốt nghiệp công nhận tốt nghiệp BM12",
            intent="graduation_conditions",
        )
    if asks_policy:
        return PlannerDecision(route="policy_retrieval", needs_retrieval=True, retrieval_intent="current_policy")

    return PlannerDecision(
        route="fallback",
        intent="out_of_scope",
        notes=["unsupported_or_low_confidence_intent"],
    )


def _asks_schedule(normalized: str) -> bool:
    return any(term in normalized for term in ("lich hoc", "thoi khoa bieu", "hom nay hoc", "tuan nay hoc"))


def _asks_grade_conversion(normalized: str) -> bool:
    conversion_terms = ("doi", "quy doi", "sang", "tuong duong", "bang may")
    grade_targets = (
        "he 4",
        "he so 4",
        "he so 10",
        "diem chu",
        "thang 4",
        "thang diem",
        "diem he 4",
        "diem he 10",
    )
    has_score = bool(re.search(r"\b\d{1,2}(?:[.,]\d+)?\b", normalized))
    asks_letter_band = bool(re.search(r"\bdiem\s*(a|b\+|b|c\+|c|d\+|d|f)\b", normalized)) or bool(
        re.search(r"\b(a|b\+|b|c\+|c|d\+|d|f)\b", normalized)
    )
    return (
        any(term in normalized for term in ("thang diem", "diem chu", "diem he 4", "diem he 10", "he so 10"))
        or (has_score and any(term in normalized for term in conversion_terms) and any(term in normalized for term in grade_targets))
        or (
            "diem" in normalized
            and asks_letter_band
            and any(term in normalized for term in ("bao nhieu", "tu may", "may diem", "la may"))
        )
    )


def _asks_graduation_ranking(normalized: str) -> bool:
    return any(term in normalized for term in ("xep loai", "bang gioi", "loai gioi", "gioi", "xuat sac", "5%")) or (
        "hoc lai" in normalized and any(term in normalized for term in ("xep", "bang", "tot nghiep", "gioi", "xuat sac"))
    ) or (
        "hoc lai" in normalized and any(term in normalized for term in ("nhieu", "co sao", "anh huong"))
    )


def _asks_rounding_policy(normalized: str) -> bool:
    return any(term in normalized for term in ("lam tron", "mot chu so thap phan")) and any(
        term in normalized for term in ("diem hoc phan", "diem", "bang diem")
    )


def _asks_training_time(normalized: str) -> bool:
    return "thoi gian dao tao" in normalized or "thoi gian toi da" in normalized or "hoc toi da" in normalized


def _asks_gpa_formula(normalized: str) -> bool:
    return ("gpa" in normalized or "diem trung binh" in normalized) and any(
        term in normalized for term in ("tinh nhu the nao", "cach tinh", "cong thuc")
    )


def _asks_special_grade_policy(normalized: str) -> bool:
    return any(
        term in normalized
        for term in (
            "diem i",
            "diem f",
            "diem r",
            "diem rt",
            "diem mt",
            "diem ct",
            "diem z",
            "diem x",
            "diem h",
        )
    )


def _asks_change_major_condition(normalized: str) -> bool:
    return "chuyen nganh" in normalized and any(term in normalized for term in ("dieu kien", "can dieu kien", "duoc chuyen"))


def _asks_graduation_registration_requirement(normalized: str) -> bool:
    return "xet tot nghiep" in normalized and any(term in normalized for term in ("khong nop", "phiếu", "phieu", "dang ky", "bm12"))


def _is_personal_graduation_query(normalized: str, has_student_id: bool) -> bool:
    return has_student_id or any(term in normalized for term in ("em", "minh", "toi", "con no", "duoc khong", "sv"))


def _asks_missing_finance_or_contact(normalized: str) -> bool:
    contact = any(term in normalized for term in ("lien he", "phong nao", "don vi nao", "gap ai", "ho tro"))
    finance = any(term in normalized for term in ("tai chinh", "hoc phi", "mien giam hoc phi", "dong tien", "cong no"))
    scholarship = any(term in normalized for term in ("hoc bong", "che do chinh sach", "tro cap"))
    return (contact and finance) or scholarship


def _asks_pending_or_discarded_current_source(normalized: str) -> bool:
    asks_bm09 = "hoan thi" in normalized or "vang thi" in normalized or "bm09" in normalized
    asks_discarded_language = "qd 3230" in normalized or ("chuan dau ra" in normalized and "ngoai ngu" in normalized)
    asks_historical_it = "qd 3297" in normalized or ("chuan" in normalized and "cntt" in normalized)
    asks_student_affairs_pending = any(term in normalized for term in ("ky luat sinh vien", "cong tac sinh vien", "qd 2658"))
    return asks_bm09 or asks_discarded_language or asks_historical_it or asks_student_affairs_pending


def _procedure_retrieval_query(normalized: str, original_query: str) -> str:
    if "rut hoc phan" in normalized:
        return "Hướng dẫn học vụ 2026 rút học phần thời hạn điều kiện"
    if "dang ky hoc phan" in normalized:
        return "Hướng dẫn học vụ 2026 đăng ký học phần"
    if "dang ky hoc lai" in normalized or "hoc lai" in normalized:
        return "Hướng dẫn học vụ 2026 đăng ký học lại học cải thiện"
    if "hoc cai thien" in normalized or "cai thien" in normalized:
        return "Hướng dẫn học vụ 2026 học cải thiện điểm đăng ký học lại"
    if "phuc khao" in normalized:
        return "Hướng dẫn học vụ 2026 phúc khảo điểm kết quả học tập"
    if "xem ket qua hoc tap" in normalized or "ket qua hoc tap o dau" in normalized:
        return "Hướng dẫn học vụ 2026 xem kết quả học tập"
    if "tam dung" in normalized or "tam ngung" in normalized:
        return "Hướng dẫn học vụ 2026 tạm dừng học tập thủ tục"
    if "huy hoc phan" in normalized or "bm10" in normalized:
        return "BM10 phiếu đề nghị hủy học phần Phòng Đào tạo C.105"
    if "mien giam" in normalized or "cong nhan diem" in normalized or "bm11" in normalized:
        return "BM11 phiếu đăng ký xét miễn giảm và công nhận điểm Phòng Đào tạo C.105"
    if "xet tot nghiep" in normalized or "ra truong" in normalized or "bm12" in normalized:
        return "BM12 phiếu đăng ký xét tốt nghiệp Điều 39"
    if "chuyen nganh" in normalized or "doi nganh" in normalized or "bm03" in normalized:
        return "BM03 phiếu đề nghị chuyển ngành đào tạo"
    if "tro lai hoc" in normalized or "bm02" in normalized:
        return "BM02 phiếu đăng ký trở lại học tập"
    if "hoc cung luc" in normalized or "hai chuong trinh" in normalized or "bm04" in normalized:
        return "BM04 phiếu đăng ký học cùng lúc hai chương trình"
    if "chuyen he" in normalized or "bm08" in normalized:
        return "BM08 phiếu đề nghị chuyển hệ đào tạo"
    return original_query


def _decision_for_pending_route(pending_route: str, has_student_id: bool) -> PlannerDecision:
    if pending_route == "student_schedule":
        return _tool_decision("student_schedule", "get_student_schedule", has_student_id)
    if pending_route == "student_grades":
        return _tool_decision("student_grades", "get_student_grades", has_student_id)
    if pending_route in {"student_graduation", "mixed_policy_student"}:
        return _mixed_decision(has_student_id, "")
    return PlannerDecision(route="fallback")


def _tool_decision(route: str, tool_name: str, has_student_id: bool) -> PlannerDecision:
    if not has_student_id:
        return PlannerDecision(
            route=route,  # type: ignore[arg-type]
            needs_tool=True,
            tool_name=tool_name,
            intent=route,
            pending_slots=["student_id"],
            clarification_questions=["Bạn cho mình biết MSSV để tra cứu dữ liệu cá nhân được không?"],
        )
    return PlannerDecision(route=route, needs_tool=True, tool_name=tool_name, intent=route)  # type: ignore[arg-type]


def _mixed_decision(has_student_id: bool, normalized: str) -> PlannerDecision:
    retrieval_query = (
        "Điều 40 cách tính điểm và xếp loại tốt nghiệp học lại quá 5% kỷ luật cảnh cáo"
        if _asks_graduation_ranking(normalized)
        else "Điều 39 điều kiện xét tốt nghiệp công nhận tốt nghiệp"
    )
    if not has_student_id:
        return PlannerDecision(
            route="mixed_policy_student",
            needs_retrieval=True,
            needs_tool=True,
            tool_name="get_graduation_snapshot",
            retrieval_query=retrieval_query,
            intent="mixed_graduation",
            pending_slots=["student_id"],
            clarification_questions=["Bạn cho mình biết MSSV để mình đối chiếu dữ liệu cá nhân với quy định tốt nghiệp nhé."],
        )
    return PlannerDecision(
        route="mixed_policy_student",
        needs_retrieval=True,
        needs_tool=True,
        tool_name="get_graduation_snapshot",
        retrieval_intent="current_policy",
        retrieval_query=retrieval_query,
        intent="mixed_graduation",
    )
