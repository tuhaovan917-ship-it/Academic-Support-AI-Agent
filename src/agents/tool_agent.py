from __future__ import annotations

from typing import Any

from src.tools import MockStudentAPI


class ToolAgent:
    def __init__(self, api: MockStudentAPI | None = None) -> None:
        self.api = api or MockStudentAPI()

    def run(self, tool_name: str, student_id: str | None, **kwargs: Any) -> dict[str, Any]:
        if not student_id:
            return {"found": False, "error": "missing_student_id"}
        if tool_name == "get_student_profile":
            return self.api.get_student_profile(student_id)
        if tool_name == "get_student_schedule":
            return self.api.get_student_schedule(student_id, semester=kwargs.get("semester"))
        if tool_name == "get_student_grades":
            return self.api.get_student_grades(student_id, semester=kwargs.get("semester"))
        if tool_name == "get_graduation_snapshot":
            return self.api.get_graduation_snapshot(student_id)
        return {"found": False, "error": f"unknown_tool:{tool_name}"}
