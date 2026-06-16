from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Route = Literal[
    "policy_retrieval",
    "procedure_or_form",
    "student_schedule",
    "student_grades",
    "student_graduation",
    "mixed_policy_student",
    "fallback",
]

Status = Literal["answered", "need_clarification", "fallback"]


@dataclass
class AgentRequest:
    query: str
    student_id: str | None = None
    session_id: str = "default"


@dataclass
class PlannerDecision:
    route: Route
    needs_retrieval: bool = False
    needs_tool: bool = False
    tool_name: str | None = None
    retrieval_intent: str = "current_policy"
    pending_slots: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    answer: str
    route: Route
    status: Status
    needs_clarification: bool = False
    clarification_questions: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    tool_results: dict[str, Any] = field(default_factory=dict)
    retrieval_results: list[dict[str, Any]] = field(default_factory=list)
    critic: dict[str, Any] = field(default_factory=dict)
    session_id: str = "default"
    student_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
