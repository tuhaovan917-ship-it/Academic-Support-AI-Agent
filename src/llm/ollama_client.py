from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from dotenv import load_dotenv

from .base import LLMError, LLMResponse
from .intent import INTENT_SYSTEM_PROMPT, build_intent_user_prompt, parse_intent_json
from .openai_client import _parse_llm_json
from .prompts import SYSTEM_PROMPT, build_user_prompt


class OllamaClient:
    provider_name = "ollama"

    def __init__(self) -> None:
        load_dotenv()
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        self.timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))

    def generate_answer(self, payload: dict[str, Any]) -> LLMResponse:
        body = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(payload)},
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LLMError(f"ollama_request_failed:{exc}") from exc
        content = data.get("message", {}).get("content")
        if not isinstance(content, str):
            raise LLMError("missing_ollama_message_content")
        return _parse_llm_json(content, raw_provider="ollama", model=self.model)

    def classify_intent(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": build_intent_user_prompt(payload)},
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LLMError(f"ollama_intent_request_failed:{exc}") from exc
        content = data.get("message", {}).get("content")
        if not isinstance(content, str):
            raise LLMError("missing_ollama_intent_content")
        return parse_intent_json(content, raw_provider="ollama", model=self.model)
