from __future__ import annotations

import os

from dotenv import load_dotenv

from .base import LLMClient, LLMError
from .mock_client import MockLLMClient


def get_llm_client() -> LLMClient:
    load_dotenv()
    provider = os.environ.get("LLM_PROVIDER", "mock").strip().lower()
    if provider in {"", "mock"}:
        return MockLLMClient()
    if provider == "openai":
        from .openai_client import OpenAIClient

        return OpenAIClient()
    if provider == "ollama":
        from .ollama_client import OllamaClient

        return OllamaClient()
    if provider in {"none", "disabled", "template"}:
        raise LLMError("llm_disabled")
    raise LLMError(f"unsupported_llm_provider:{provider}")
