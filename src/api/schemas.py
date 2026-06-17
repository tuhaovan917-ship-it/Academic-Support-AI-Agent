from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ResponseMode = Literal["compact", "debug"]


@dataclass
class AgentServiceRequest:
    query: str
    session_id: str | None = None
    student_id: str | None = None
    include_debug: bool = False
    include_retrieval: bool = False
    include_tool_results: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentServiceRequest":
        return cls(
            query=str(payload.get("query") or ""),
            session_id=payload.get("session_id"),
            student_id=payload.get("student_id"),
            include_debug=bool(payload.get("include_debug", False)),
            include_retrieval=bool(payload.get("include_retrieval", False)),
            include_tool_results=bool(payload.get("include_tool_results", True)),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentServiceResponse:
    answer: str
    status: str
    route: str
    session_id: str
    student_id: str | None = None
    needs_clarification: bool = False
    clarification_questions: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    tool_results: dict[str, Any] | None = None
    retrieval_results: list[dict[str, Any]] | None = None
    critic: dict[str, Any] | None = None
    planner: dict[str, Any] | None = None
    llm: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}
