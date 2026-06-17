from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv

from .mock_student_api import MockStudentAPI


class StudentClient(Protocol):
    def get_student_profile(self, student_id: str) -> dict[str, Any]:
        ...

    def get_student_schedule(self, student_id: str, semester: str | None = None) -> dict[str, Any]:
        ...

    def get_student_grades(self, student_id: str, semester: str | None = None) -> dict[str, Any]:
        ...

    def get_graduation_snapshot(self, student_id: str) -> dict[str, Any]:
        ...


class HttpStudentClient:
    """HTTP adapter for Task 3 or a future .NET backend.

    Expected endpoints are documented in docs/contracts/student_api_contract.md.
    The adapter normalizes transport failures into stable tool error payloads.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10,
        token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.token = token

    def get_student_profile(self, student_id: str) -> dict[str, Any]:
        return self._get(f"/students/{student_id.upper()}/profile")

    def get_student_schedule(self, student_id: str, semester: str | None = None) -> dict[str, Any]:
        query = {"semester": semester} if semester else None
        return self._get(f"/students/{student_id.upper()}/schedule", query=query)

    def get_student_grades(self, student_id: str, semester: str | None = None) -> dict[str, Any]:
        query = {"semester": semester} if semester else None
        return self._get(f"/students/{student_id.upper()}/grades", query=query)

    def get_graduation_snapshot(self, student_id: str) -> dict[str, Any]:
        return self._get(f"/students/{student_id.upper()}/graduation-snapshot")

    def _get(self, path: str, query: dict[str, str | None] | None = None) -> dict[str, Any]:
        url = self.base_url + path
        if query:
            clean_query = {key: value for key, value in query.items() if value}
            if clean_query:
                url += "?" + urllib.parse.urlencode(clean_query)
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {"found": False, "error": "student_not_found", "source": "http"}
            return {"found": False, "error": f"student_api_http_error:{exc.code}", "source": "http"}
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            return {"found": False, "error": f"student_api_unavailable:{exc}", "source": "http"}
        except json.JSONDecodeError as exc:
            return {"found": False, "error": f"student_api_invalid_json:{exc}", "source": "http"}
        if not isinstance(payload, dict):
            return {"found": False, "error": "student_api_invalid_payload", "source": "http"}
        payload.setdefault("source", "http")
        return payload


def get_student_client() -> StudentClient:
    load_dotenv()
    provider = os.environ.get("STUDENT_API_PROVIDER", "mock").strip().lower()
    if provider in {"", "mock"}:
        mock_dir_raw = os.environ.get("STUDENT_MOCK_DIR")
        return MockStudentAPI(Path(mock_dir_raw)) if mock_dir_raw else MockStudentAPI()
    if provider in {"http", "api", "dotnet"}:
        base_url = os.environ.get("STUDENT_API_BASE_URL", "").strip()
        if not base_url:
            return _ConfigErrorClient("student_api_missing_base_url")
        timeout = _float_env("STUDENT_API_TIMEOUT_SECONDS", 10)
        token = os.environ.get("STUDENT_API_TOKEN") or None
        return HttpStudentClient(base_url, timeout_seconds=timeout, token=token)
    return _ConfigErrorClient(f"unsupported_student_api_provider:{provider}")


class _ConfigErrorClient:
    def __init__(self, error: str) -> None:
        self.error = error

    def get_student_profile(self, student_id: str) -> dict[str, Any]:
        return self._payload(student_id)

    def get_student_schedule(self, student_id: str, semester: str | None = None) -> dict[str, Any]:
        return self._payload(student_id)

    def get_student_grades(self, student_id: str, semester: str | None = None) -> dict[str, Any]:
        return self._payload(student_id)

    def get_graduation_snapshot(self, student_id: str) -> dict[str, Any]:
        return self._payload(student_id)

    def _payload(self, student_id: str) -> dict[str, Any]:
        return {"found": False, "student_id": student_id.upper(), "error": self.error, "source": "config"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default
