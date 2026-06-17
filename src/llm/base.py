from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class LLMError(RuntimeError):
    """Raised when an LLM provider cannot return a usable answer."""


@dataclass
class LLMResponse:
    answer: str
    used_citations: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient(Protocol):
    provider_name: str

    def generate_answer(self, payload: dict[str, Any]) -> LLMResponse:
        ...

    def classify_intent(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...
