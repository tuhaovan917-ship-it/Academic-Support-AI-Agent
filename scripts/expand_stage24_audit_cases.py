from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = PROJECT_ROOT / "data" / "review" / "audit_cases.jsonl"
SUMMARY_PATH = PROJECT_ROOT / "data" / "review" / "stage24_expanded_audit_plan.md"
TARGET_TOTAL = 100
TRIM_IF_OVER_TARGET = {
    "training_program_structure",
    "minimum_graduation_competency",
}


NEW_CASES: list[dict[str, Any]] = [
    {
        "case_id": "definition_program_training",
        "query": "Trong QĐ-3344, chương trình đào tạo được hiểu là gì?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "2",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "learning_outcome_clo_plo",
        "query": "Chuẩn đầu ra học phần CLO và chuẩn đầu ra chương trình PLO được quy định như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "3",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "course_types_required_elective",
        "query": "Học phần bắt buộc, tự chọn, thay thế và tiên quyết khác nhau như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "6",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "course_sequence_prerequisite",
        "query": "Học phần tiên quyết, học phần trước và học phần song hành được hiểu ra sao?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "6",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "training_method_credit_system",
        "query": "HUIT tổ chức đào tạo theo phương thức tín chỉ như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "7",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "online_exam_conditions",
        "query": "Thi và đánh giá trực tuyến được chấp nhận trong điều kiện nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "8",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "student_categories_second_degree",
        "query": "Người học văn bằng thứ hai và liên thông đại học được quy định ra sao?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "10",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "auditing_student_rule",
        "query": "Người học dự thính tại HUIT là ai và có quyền lợi gì?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "10",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "student_rights",
        "query": "Sinh viên HUIT có những quyền gì trong quá trình học tập?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "12",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "training_program_structure",
        "query": "Chương trình đào tạo gồm mục tiêu, chuẩn đầu ra và đề cương học phần như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "14",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "course_syllabus_required_fields",
        "query": "Đề cương học phần phải thể hiện những thông tin nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "14",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "curriculum_update_publication",
        "query": "Khi chương trình đào tạo thay đổi thì nhà trường phải công bố cho sinh viên như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "15",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "minimum_graduation_competency",
        "query": "Yêu cầu năng lực tối thiểu sau tốt nghiệp gồm kiến thức, kỹ năng và trách nhiệm gì?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "16",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "teaching_plan_publication",
        "query": "Kế hoạch giảng dạy và học tập được công bố cho sinh viên như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "17",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "training_time_engineer_regular",
        "query": "Đại học chính quy cấp bằng kỹ sư có thời gian thiết kế và thời gian tối đa bao lâu?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "18",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "training_time_second_degree_engineer",
        "query": "Đại học văn bằng thứ hai cấp bằng kỹ sư được học tối đa mấy học kỳ?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "18",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "new_student_account_card",
        "query": "Khi nhập học sinh viên được cấp thẻ sinh viên và tài khoản cá nhân như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "19",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "freshman_citizen_week",
        "query": "Tân sinh viên có phải tham gia tuần lễ sinh hoạt công dân không?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "19",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "major_assignment_after_general_stage",
        "query": "Sau giai đoạn giáo dục đại cương sinh viên được đăng ký nguyện vọng ngành thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "20",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "summer_semester_credit_limit",
        "query": "Học kỳ hè có giới hạn số tín chỉ tối thiểu không?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "21",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "regular_low_gpa_credit_limit",
        "query": "Sinh viên chính quy có GPA tích lũy dưới 2,00 được đăng ký tối đa bao nhiêu tín chỉ?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "21",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "course_registration_late_payment",
        "query": "Nếu chưa đóng học phí đúng hạn thì việc đăng ký học phần bị xử lý thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "21",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "withdraw_course_refund_exception",
        "query": "Rút học phần có được hoàn học phí không và trường hợp ngoại lệ là gì?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "22",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "private_leave_max_absence_25_percent",
        "query": "Nghỉ ốm hoặc việc riêng tối đa không quá bao nhiêu phần trăm số giờ học trên lớp?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "23",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "temporary_leave_personal_condition",
        "query": "Xin tạm dừng học tập vì nhu cầu cá nhân cần GPA bao nhiêu và học tối thiểu bao lâu?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "24",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "temporary_leave_return_timing",
        "query": "Khi hết thời gian tạm dừng học tập sinh viên phải xin tiếp nhận lại trước thời điểm nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "24",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "major_transfer_once_only",
        "query": "Sinh viên được chuyển ngành mấy lần trong toàn khóa học?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "25",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "student_exchange_credit_recognition",
        "query": "Trao đổi sinh viên và công nhận tín chỉ giữa các cơ sở đào tạo được quy định thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "26",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "dual_program_stop_condition",
        "query": "Đang học song ngành mà GPA chương trình thứ nhất dưới 2,0 thì xử lý thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "27",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "transfer_school_deadline",
        "query": "Thủ tục chuyển trường phải hoàn thành trước học kỳ mới bao lâu?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "28",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "dropout_due_to_max_training_time",
        "query": "Bị buộc thôi học vì hết thời gian đào tạo tối đa có thể chuyển sang hệ vừa làm vừa học không?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "29",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "process_score_weight_limit",
        "query": "Điểm đánh giá quá trình được chiếm tối đa bao nhiêu phần trăm điểm học phần?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "30",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "course_reassessment_limit_d_or_c",
        "query": "Thi lại hoặc đánh giá lại điểm thành phần để từ không đạt thành đạt thì điểm bị giới hạn mức nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "30",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "score_conversion_b_plus",
        "query": "Điểm B+ tương ứng thang điểm 10 và thang điểm 4 như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "30",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "special_score_rt_h",
        "query": "Điểm RT và điểm H trong bảng kết quả học tập có ý nghĩa gì?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "30",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "i_score_late_application_7_days",
        "query": "Đơn xin điểm I nộp trễ quá 7 ngày có được xem xét không?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "30",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "course_exemption_before_registration_two_weeks",
        "query": "Hồ sơ miễn giảm học phần phải nộp trước đăng ký học phần bao lâu?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "31",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "max_exempted_credit_50_percent",
        "query": "Khối lượng tối đa được miễn giảm và chuyển điểm có vượt quá 50% chương trình không?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "31",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "gpa_formula_ai_ni",
        "query": "Công thức GPA dùng ai và ni trong Điều 32 được hiểu như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "32",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "grade_appeal_deadline",
        "query": "Sinh viên được phúc khảo điểm trong thời hạn nào sau khi công bố điểm?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "33",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "semester_result_publication",
        "query": "Kết quả học tập học kỳ được công bố và lưu trữ ra sao?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "34",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "year_rank_credit_thresholds",
        "query": "Tích lũy bao nhiêu tín chỉ thì được xếp năm thứ hai, thứ ba, thứ tư?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "35",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "recognition_transfer_max_50_percent",
        "query": "Khối lượng tối đa được công nhận chuyển đổi từ chương trình khác là bao nhiêu?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "36",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "thesis_committee_min_members",
        "query": "Hội đồng chấm khóa luận tốt nghiệp tối thiểu bao nhiêu thành viên?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "37",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "thesis_grade_publication_7_days",
        "query": "Kết quả chấm khóa luận tốt nghiệp được công bố trong bao lâu?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "38",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "graduation_no_application_no_review",
        "query": "Không nộp phiếu đăng ký xét tốt nghiệp thì có được xét tốt nghiệp không?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "39",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "graduation_ceremony_months",
        "query": "HUIT tổ chức lễ tốt nghiệp và trao bằng vào tháng mấy hằng năm?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "39",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "excellent_graduation_discipline_downgrade",
        "query": "Bị kỷ luật cảnh cáo cấp trường có làm giảm hạng tốt nghiệp Xuất sắc hoặc Giỏi không?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "40",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "unfinished_graduation_conditions_three_years",
        "query": "Hết thời gian học tối đa nhưng còn thiếu GDQP, GDTC, ngoại ngữ hoặc CNTT thì có thời hạn hoàn thiện bao lâu?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "41",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "training_records_permanent_storage",
        "query": "Quyết định trúng tuyển, bảng điểm gốc và sổ cấp bằng được lưu trữ như thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "42",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "training_inspection_rule",
        "query": "Nhà trường kiểm tra công tác đào tạo tại các đơn vị theo quy định nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "43",
        "expected_source_type": "regulation",
    },
    {
        "case_id": "training_reward_rule",
        "query": "Cá nhân, tập thể và người học có thành tích trong đào tạo được khen thưởng thế nào?",
        "intent": "current_policy",
        "expected_document_id": "huit_qd_3344_2025",
        "expected_article_number": "44",
        "expected_source_type": "regulation",
    },
]


def read_cases() -> list[dict[str, Any]]:
    if not CASES_PATH.exists():
        return []
    with CASES_PATH.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_cases(cases: list[dict[str, Any]]) -> None:
    with CASES_PATH.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    cases = read_cases()
    existing_ids = {case["case_id"] for case in cases}
    added = [case for case in NEW_CASES if case["case_id"] not in existing_ids]
    cases.extend(added)
    if len(cases) > TARGET_TOTAL:
        trimmed_cases: list[dict[str, Any]] = []
        removed = 0
        for case in cases:
            if len(cases) - removed <= TARGET_TOTAL:
                trimmed_cases.append(case)
            elif case["case_id"] in TRIM_IF_OVER_TARGET:
                removed += 1
            else:
                trimmed_cases.append(case)
        cases = trimmed_cases
    write_cases(cases)

    by_status: dict[str, int] = {}
    by_doc: dict[str, int] = {}
    for case in cases:
        by_status[case.get("expected_status", "active")] = by_status.get(case.get("expected_status", "active"), 0) + 1
        doc = case.get("expected_document_id", "unknown")
        by_doc[doc] = by_doc.get(doc, 0) + 1

    lines = [
        "# Stage 24 - Expanded Retrieval Audit Plan",
        "",
        "## Input",
        "",
        "- Existing audit cases: `data/review/audit_cases.jsonl`",
        "- Current vector DB: `huit_db`",
        "- Primary current regulation: `huit_qd_3344_2025`",
        "",
        "## Output",
        "",
        f"- Added cases: `{len(added)}`",
        f"- Total cases: `{len(cases)}`",
        "",
        "## Coverage",
        "",
        f"- By status: `{by_status}`",
        f"- By expected document: `{by_doc}`",
        "",
        "## Process",
        "",
        "1. Added 50 new cases covering definitions, program structure, registration limits, leave, transfer, assessment tables, GPA, thesis, graduation, storage, inspection, and reward rules.",
        "2. Kept pending/discarded cases in the suite to ensure blocked sources stay out of current-policy answers.",
        "3. Next command should run `scripts/audit_retrieval.py` and inspect any failures.",
    ]
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"added": len(added), "total": len(cases), "summary": str(SUMMARY_PATH.relative_to(PROJECT_ROOT))}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
