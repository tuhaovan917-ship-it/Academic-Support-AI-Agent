from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    session_id: str
    student_id: str | None = None
    last_route: str | None = None
    pending_slots: list[str] = field(default_factory=list)
    last_user_query: str | None = None
    turns: list[dict[str, Any]] = field(default_factory=list)


_SESSIONS: dict[str, SessionState] = {}


def get_session(session_id: str) -> SessionState:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = SessionState(session_id=session_id)
    return _SESSIONS[session_id]


def update_session(
    session_id: str,
    *,
    query: str,
    answer: str,
    route: str,
    student_id: str | None = None,
    pending_slots: list[str] | None = None,
) -> SessionState:
    state = get_session(session_id)
    if student_id:
        state.student_id = student_id
    state.last_route = route
    state.pending_slots = pending_slots or []
    state.last_user_query = query
    state.turns.append({"query": query, "answer": answer, "route": route})
    state.turns = state.turns[-10:]
    return state
