from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MOCK_DIR = PROJECT_ROOT / "data" / "mock"


class MockStudentAPI:
    def __init__(self, mock_dir: Path = MOCK_DIR) -> None:
        self.mock_dir = mock_dir
        self.students = self._load("students.json")
        self.schedules = self._load("schedules.json")
        self.grades = self._load("grades.json")

    def _load(self, filename: str) -> dict[str, Any]:
        path = self.mock_dir / filename
        return json.loads(path.read_text(encoding="utf-8"))

    def get_student_profile(self, student_id: str) -> dict[str, Any]:
        student = self.students.get(student_id.upper())
        if not student:
            return {"found": False, "student_id": student_id.upper(), "error": "student_not_found"}
        return {"found": True, **student}

    def get_student_schedule(self, student_id: str, semester: str | None = None) -> dict[str, Any]:
        student_id = student_id.upper()
        profile = self.get_student_profile(student_id)
        if not profile.get("found"):
            return profile
        items = self.schedules.get(student_id, [])
        if semester:
            items = [item for item in items if item.get("semester") == semester]
        return {"found": True, "student_id": student_id, "schedule": items}

    def get_student_grades(self, student_id: str, semester: str | None = None) -> dict[str, Any]:
        student_id = student_id.upper()
        profile = self.get_student_profile(student_id)
        if not profile.get("found"):
            return profile
        payload = self.grades.get(student_id, {})
        courses = payload.get("courses", [])
        if semester:
            courses = [item for item in courses if item.get("semester") == semester]
        failed_courses = [item for item in courses if item.get("status") == "failed"]
        return {
            "found": True,
            "student_id": student_id,
            "cumulative_gpa": payload.get("cumulative_gpa"),
            "total_credits": payload.get("total_credits"),
            "retaken_credits": payload.get("retaken_credits"),
            "retake_ratio": payload.get("retake_ratio"),
            "courses": courses,
            "failed_courses": failed_courses,
        }

    def get_graduation_snapshot(self, student_id: str) -> dict[str, Any]:
        student_id = student_id.upper()
        profile = self.get_student_profile(student_id)
        if not profile.get("found"):
            return profile
        grade_info = self.get_student_grades(student_id)
        missing_certificates = [
            name
            for name, passed in profile.get("certificates", {}).items()
            if not passed
        ]
        failed_courses = grade_info.get("failed_courses", [])
        eligible = (
            not failed_courses
            and (grade_info.get("cumulative_gpa") or 0) >= 2.0
            and not missing_certificates
        )
        warnings: list[str] = []
        if (grade_info.get("retake_ratio") or 0) > 0.05:
            warnings.append("retake_ratio_over_5_percent")
        if profile.get("disciplinary_warning"):
            warnings.append("disciplinary_warning")
        return {
            "found": True,
            "student_id": student_id,
            "full_name": profile.get("full_name"),
            "major": profile.get("major"),
            "cumulative_gpa": grade_info.get("cumulative_gpa"),
            "total_credits": grade_info.get("total_credits"),
            "retaken_credits": grade_info.get("retaken_credits"),
            "retake_ratio": grade_info.get("retake_ratio"),
            "failed_courses": failed_courses,
            "missing_certificates": missing_certificates,
            "eligible_for_graduation": eligible,
            "warnings": warnings,
        }
