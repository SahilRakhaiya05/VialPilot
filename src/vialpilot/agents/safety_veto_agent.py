from __future__ import annotations

from typing import Any, Dict

from src.vialpilot.agents.base import from_llm, local_output
from src.vialpilot.llm.client import run_json  # noqa: used in force_allow branch
from src.vialpilot.models.schemas import AgentOutput

SYSTEM = """You are the Safety Veto Agent. Block unsafe lab actions.
Return JSON: {"allow":true,"risk_level":"low|medium|high|critical","reason":"","required_change":"","safe_alternative":""}"""


class SafetyVetoAgent:
    name = "SafetyVetoAgent"

    def run(
        self,
        subtask: Dict[str, Any],
        vision: Dict[str, Any],
        scene_state: Dict[str, Any],
        force_allow: bool = False,
    ) -> AgentOutput:
        if force_allow:
            return local_output(
                self.name,
                data={
                    "allow": True, "risk_level": "medium",
                    "reason": "Human operator confirmed action.",
                    "required_change": "", "safe_alternative": "",
                },
                summary="Human confirmation received — proceeding with caution.",
                confidence=0.85,
            )
        target = subtask.get("target_object")
        obj = next((o for o in vision.get("objects", []) if o.get("id") == target), {})
        hazards = vision.get("hazards", []) or scene_state.get("hazards", [])
        destination = subtask.get("destination")

        if obj.get("confidence", 1.0) < 0.7 or destination == "human_confirmation":
            fallback = {
                "allow": False,
                "risk_level": "high",
                "reason": "Object identity is visually uncertain.",
                "required_change": "Request clearer frame or human confirmation.",
                "safe_alternative": "REQUEST_HUMAN_CONFIRMATION",
            }
        elif hazards:
            fallback = {
                "allow": True,
                "risk_level": "medium",
                "reason": "Hazard present; require safe routing.",
                "required_change": "Use around_hazard route.",
                "safe_alternative": "MOVE_AROUND_CONTAMINATED_ZONE",
            }
        else:
            fallback = {
                "allow": True,
                "risk_level": "low",
                "reason": "Object visible and destination valid.",
                "required_change": "",
                "safe_alternative": "",
            }

        prompt = f"Subtask: {subtask}\nVision: {vision}\nScene: {scene_state}"
        llm = run_json(agent_name=self.name, system_prompt=SYSTEM, user_prompt=prompt, fallback_json=fallback)
        allowed = llm.json.get("allow", False)
        output = from_llm(
            self.name,
            llm,
            summary="Action approved." if allowed else f"Blocked: {llm.json.get('reason', '')}",
            confidence=0.95 if allowed else 0.7,
        )
        if not allowed:
            output.status = "blocked"
        elif llm.json.get("risk_level") in ("medium", "high", "critical"):
            output.status = "warning"
        return output


safety_veto_agent = SafetyVetoAgent()