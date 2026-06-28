"""Base utilities for agent output formatting."""
from __future__ import annotations

from typing import Any, Dict, Literal

from src.vialpilot.models.schemas import AgentOutput, LLMResult

AgentStatus = Literal["success", "warning", "blocked", "failed"]


def from_llm(agent_name: str, llm: LLMResult, summary: str, confidence: float = 0.9) -> AgentOutput:
    status: AgentStatus = "success"
    if llm.error and not llm.json:
        status = "failed"
        summary = f"AI call failed: {llm.error}"
    elif llm.error:
        status = "warning"
    data = dict(llm.json)
    data["llm_model"] = llm.model
    data["llm_mode"] = llm.mode
    if llm.raw_text:
        data["llm_raw_preview"] = llm.raw_text[:2000]
    if llm.error:
        data["llm_error"] = llm.error
    return AgentOutput(
        agent_name=agent_name,
        status=status,
        summary=summary,
        confidence=confidence,
        data=data,
        latency_ms=llm.latency_ms,
        mode=llm.mode,
    )


def local_output(
    agent_name: str,
    data: Dict[str, Any],
    summary: str,
    *,
    status: AgentStatus = "success",
    confidence: float = 1.0,
    latency_ms: float = 0.0,
) -> AgentOutput:
    return AgentOutput(
        agent_name=agent_name,
        status=status,
        summary=summary,
        confidence=confidence,
        data=data,
        latency_ms=latency_ms,
        mode="real",
    )