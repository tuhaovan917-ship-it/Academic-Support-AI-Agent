from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from .base import LLMError, LLMResponse
from .intent import INTENT_SYSTEM_PROMPT, build_intent_user_prompt, parse_intent_json
from .prompts import SYSTEM_PROMPT, build_user_prompt


class OpenAIClient:
    provider_name = "openai"

    def __init__(self) -> None:
        load_dotenv()
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        self.timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMError("missing_openai_api_key")

    def generate_answer(self, payload: dict[str, Any]) -> LLMResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("openai_package_not_installed") from exc

        client = OpenAI(timeout=self.timeout)
        try:
            completion = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(payload)},
                ],
            )
            content = completion.choices[0].message.content or "{}"
        except Exception as exc:  # pragma: no cover - provider/network dependent
            raise LLMError(f"openai_request_failed:{exc}") from exc
        return _parse_llm_json(content, raw_provider="openai", model=self.model)

    def classify_intent(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("openai_package_not_installed") from exc

        client = OpenAI(timeout=self.timeout)
        try:
            completion = client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": build_intent_user_prompt(payload)},
                ],
            )
            content = completion.choices[0].message.content or "{}"
        except Exception as exc:  # pragma: no cover - provider/network dependent
            raise LLMError(f"openai_intent_request_failed:{exc}") from exc
        return parse_intent_json(content, raw_provider="openai", model=self.model)


def _parse_llm_json(content: str, *, raw_provider: str, model: str) -> LLMResponse:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError("invalid_llm_json") from exc
    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise LLMError("missing_llm_answer")
    return LLMResponse(
        answer=answer.strip(),
        used_citations=_string_list(data.get("used_citations")),
        safety_notes=_string_list(data.get("safety_notes")),
        missing_information=_string_list(data.get("missing_information")),
        raw={"provider": raw_provider, "model": model},
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]
