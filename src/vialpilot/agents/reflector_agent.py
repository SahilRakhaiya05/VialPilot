from __future__ import annotations

from typing import Any, Dict

from src.vialpilot.agents.base import from_llm
from src.vialpilot.llm.client import run_json
from src.vialpilot.models.schemas import AgentOutput

SYSTEM = """You are the Reflector Agent. Verify whether the latest action succeeded.
Return JSON: {"success":true,"evidence":"","failed_reason":"","retry_needed":false,"next_recommendation":""}"""


class ReflectorAgent:
    name = "ReflectorAgent"

    def run(self, subtask: Dict[str, Any], actor_result: Dict[str, Any], scene_state: Dict[str, Any]) -> AgentOutput:
        if actor_result.get("applied"):
            fallback = {
                "success": True,
                "evidence": actor_result.get("message", "State updated."),
                "failed_reason": "",
                "retry_needed": False,
                "next_recommendation": "Continue to next subtask.",
            }
        else:
            fallback = {
                "success": False,
                "evidence": actor_result.get("message", "No movement applied."),
                "failed_reason": actor_result.get("message", "Action blocked."),
                "retry_needed": True,
                "next_recommendation": "Replan or request human confirmation.",
            }
        prompt = f"Subtask: {subtask}\nActor: {actor_result}\nState: {scene_state}"
        llm = run_json(agent_name=self.name, system_prompt=SYSTEM, user_prompt=prompt, fallback_json=fallback)
        output = from_llm(
            self.name,
            llm,
            summary="Verified success." if llm.json.get("success") else f"Failed: {llm.json.get('failed_reason', '')}",
            confidence=0.9 if llm.json.get("success") else 0.6,
        )
        if not llm.json.get("success"):
            output.status = "warning"
        return output


reflector_agent = ReflectorAgent()