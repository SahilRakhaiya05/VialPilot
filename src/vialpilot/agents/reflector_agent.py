from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.vialpilot.agents.base import from_llm
from src.vialpilot.llm.client import run_json
from src.vialpilot.llm.images import ImageFrame
from src.vialpilot.models.schemas import AgentOutput

SYSTEM = """You are the Reflector Agent. Verify whether the latest robot action succeeded.
When a post-action camera frame is provided, compare it to the expected outcome (object moved, gripper state, zone placement).
Return JSON: {"success":true,"evidence":"","failed_reason":"","retry_needed":false,"next_recommendation":"","visual_match":true}"""


class ReflectorAgent:
    name = "ReflectorAgent"

    def run(
        self,
        subtask: Dict[str, Any],
        actor_result: Dict[str, Any],
        scene_state: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png",
        frames: Optional[List[ImageFrame]] = None,
        is_replan: bool = False,
    ) -> AgentOutput:
        applied = actor_result.get("applied")
        if applied:
            fallback = {
                "success": True,
                "evidence": actor_result.get("message", "State updated."),
                "failed_reason": "",
                "retry_needed": False,
                "next_recommendation": "Continue to next subtask.",
                "visual_match": True,
            }
        else:
            fallback = {
                "success": False,
                "evidence": actor_result.get("message", "No movement applied."),
                "failed_reason": actor_result.get("message", "Action blocked."),
                "retry_needed": not is_replan,
                "next_recommendation": "Replan with alternate route or slower approach.",
                "visual_match": False,
            }
        replan_note = " (replan attempt)" if is_replan else ""
        prompt = (
            f"Subtask: {subtask}\nActor: {actor_result}\nState: {scene_state}{replan_note}\n"
            "Verify success using structured state and any post-action image."
        )
        llm = run_json(
            agent_name=self.name,
            system_prompt=SYSTEM,
            user_prompt=prompt,
            fallback_json=fallback,
            image_bytes=image_bytes,
            image_mime=image_mime,
            images=frames,
        )
        output = from_llm(
            self.name,
            llm,
            summary="Verified success." if llm.json.get("success") else f"Failed: {llm.json.get('failed_reason', '')}",
            confidence=0.9 if llm.json.get("success") else 0.6,
        )
        if not llm.json.get("success"):
            output.status = "warning"
        if is_replan:
            llm.json["retry_needed"] = False
            output.data = llm.json
        return output


reflector_agent = ReflectorAgent()