from __future__ import annotations


def fallback_answer(reason: str | None = None) -> str:
    suffix = f" Lý do kỹ thuật: {reason}." if reason else ""
    return (
        "Mình chưa đủ căn cứ để trả lời chắc chắn câu này. "
        "Bạn nên liên hệ Phòng Đào tạo hoặc chuyên viên học vụ để được xác nhận chính thức."
        + suffix
    )
