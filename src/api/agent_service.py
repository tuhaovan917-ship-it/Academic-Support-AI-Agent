from __future__ import annotations

import uuid
from typing import Any

from src.agents import run_agent

from .errors import ERR_INTERNAL, ERR_MISSING_QUERY, ServiceError, error_from_agent
from .schemas import AgentServiceRequest, AgentServiceResponse


class AgentService:
    def ask(self, request: AgentServiceRequest | dict[str, Any]) -> AgentServiceResponse:
        service_request = request if isinstance(request, AgentServiceRequest) else AgentServiceRequest.from_dict(request)
        session_id = service_request.session_id or self._new_session_id()
        query = service_request.query.strip()
        if not query:
            return AgentServiceResponse(
                answer="Bạn vui lòng nhập câu hỏi cần tư vấn.",
                status="fallback",
                route="fallback",
                session_id=session_id,
                student_id=service_request.student_id,
                needs_clarification=True,
                clarification_questions=["Bạn muốn hỏi nội dung học vụ nào?"],
                error=ServiceError(ERR_MISSING_QUERY, "Thiếu nội dung câu hỏi.").to_dict(),
                metadata={"service": "agent_service"},
            )

        try:
            agent_response = run_agent(
                query=query,
                student_id=service_request.student_id,
                session_id=session_id,
            )
            return self._from_agent_response(agent_response.to_dict(), service_request, session_id)
        except Exception as exc:  # pragma: no cover - defensive service boundary
            return AgentServiceResponse(
                answer="Hệ thống đang gặp lỗi nội bộ khi xử lý yêu cầu.",
                status="fallback",
                route="fallback",
                session_id=session_id,
                student_id=service_request.student_id,
                error=ServiceError(ERR_INTERNAL, "Lỗi nội bộ AgentService.", {"exception": str(exc)}).to_dict(),
                metadata={"service": "agent_service"},
            )

    def _from_agent_response(
        self,
        payload: dict[str, Any],
        request: AgentServiceRequest,
        session_id: str,
    ) -> AgentServiceResponse:
        error = error_from_agent(payload)
        include_debug = request.include_debug
        include_retrieval = request.include_retrieval or include_debug
        include_tool = request.include_tool_results or include_debug
        return AgentServiceResponse(
            answer=payload.get("answer") or "",
            status=payload.get("status") or "fallback",
            route=payload.get("route") or "fallback",
            session_id=session_id,
            student_id=payload.get("student_id"),
            needs_clarification=bool(payload.get("needs_clarification")),
            clarification_questions=list(payload.get("clarification_questions") or []),
            citations=list(payload.get("citations") or []),
            error=error.to_dict() if error else None,
            tool_results=payload.get("tool_results") if include_tool else None,
            retrieval_results=payload.get("retrieval_results") if include_retrieval else None,
            critic=payload.get("critic") if include_debug else None,
            planner=payload.get("planner") if include_debug else None,
            llm=payload.get("llm") if include_debug else None,
            metadata={
                "service": "agent_service",
                "response_mode": "debug" if include_debug else "compact",
                **request.metadata,
            },
        )

    def _new_session_id(self) -> str:
        return f"session_{uuid.uuid4().hex}"
