from __future__ import annotations

from .answering_agent import answer
from .critic_agent import critique
from .fallback import fallback_answer
from .models import AgentRequest, AgentResponse
from .planner import extract_student_id, plan
from .retriever_agent import retrieve
from .tool_agent import ToolAgent
from src.memory import get_session, update_session


def run_agent(
    query: str,
    student_id: str | None = None,
    session_id: str = "default",
    *,
    tool_agent: ToolAgent | None = None,
) -> AgentResponse:
    request = AgentRequest(query=query, student_id=student_id, session_id=session_id)
    session = get_session(request.session_id)
    detected_student_id = extract_student_id(request.query)
    effective_student_id = request.student_id or detected_student_id or session.student_id
    pending_route = session.last_route if session.pending_slots else None

    decision = plan(request.query, student_id=effective_student_id, pending_route=pending_route)

    if decision.pending_slots:
        response = AgentResponse(
            answer=decision.clarification_questions[0],
            route=decision.route,
            status="need_clarification",
            needs_clarification=True,
            clarification_questions=decision.clarification_questions,
            critic={"passed": True, "warnings": decision.pending_slots},
            session_id=request.session_id,
            student_id=effective_student_id,
        )
        update_session(
            request.session_id,
            query=request.query,
            answer=response.answer,
            route=decision.route,
            student_id=effective_student_id,
            pending_slots=decision.pending_slots,
        )
        return response

    retrieval_results = []
    if decision.needs_retrieval:
        retrieval_query = _retrieval_query_for_route(request.query, decision.route)
        retrieval_results = retrieve(retrieval_query, intent=decision.retrieval_intent, k=5)

    tool_result = {}
    if decision.needs_tool and decision.tool_name:
        tool_result = (tool_agent or ToolAgent()).run(decision.tool_name, effective_student_id)

    if decision.route == "fallback":
        response = AgentResponse(
            answer=fallback_answer(),
            route=decision.route,
            status="fallback",
            critic={"passed": True, "warnings": decision.notes},
            session_id=request.session_id,
            student_id=effective_student_id,
        )
        update_session(request.session_id, query=request.query, answer=response.answer, route=decision.route)
        return response

    final_answer, citations = answer(
        query=request.query,
        decision=decision,
        retrieval_results=retrieval_results,
        tool_result=tool_result,
        student_id=effective_student_id,
    )
    critic = critique(decision, final_answer, citations, retrieval_results, tool_result, effective_student_id)
    status = "answered" if critic.get("passed") else "fallback"
    if status == "fallback":
        final_answer = fallback_answer("; ".join(critic.get("errors", [])))

    response = AgentResponse(
        answer=final_answer,
        route=decision.route,
        status=status,
        needs_clarification=False,
        citations=citations,
        tool_results=tool_result,
        retrieval_results=retrieval_results,
        critic=critic,
        session_id=request.session_id,
        student_id=effective_student_id,
    )
    update_session(
        request.session_id,
        query=request.query,
        answer=response.answer,
        route=decision.route,
        student_id=effective_student_id,
        pending_slots=[],
    )
    return response


def _retrieval_query_for_route(query: str, route: str) -> str:
    if route == "mixed_policy_student":
        lowered = query.lower()
        if any(term in lowered for term in ("xếp loại", "xep loai", "giỏi", "gioi", "xuất sắc", "xuat sac", "học lại", "hoc lai", "5%")):
            return "Điều 40 cách tính điểm và xếp loại tốt nghiệp học lại quá 5%"
        return "Điều kiện xét tốt nghiệp và xếp loại tốt nghiệp theo QĐ-3344"
    return query
