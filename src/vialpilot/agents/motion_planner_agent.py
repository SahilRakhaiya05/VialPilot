from __future__ import annotations

from typing import Any, Dict

from src.vialpilot.agents.base import from_llm
from src.vialpilot.llm.client import run_json
from src.vialpilot.models.schemas import AgentOutput

SYSTEM = """You are the Motion Planner Agent. Convert approved subtasks to robot commands.
Commands: PICK_OBJECT, PLACE_OBJECT, MOVE_TO, SCAN_AREA, WAIT, REQUEST_HUMAN_CONFIRMATION, COMPLETE_TASK, ABORT_TASK.
Return JSON: {"command":"","object_id":"","from":"","to":"","parameters":{},"reason":""}"""


class MotionPlannerAgent:
    name = "MotionPlannerAgent"

    def run(self, subtask: Dict[str, Any], safety: Dict[str, Any], localizer: Dict[str, Any]) -> AgentOutput:
        if not safety.get("allow", False):
            command = {
                "command": "REQUEST_HUMAN_CONFIRMATION",
                "object_id": subtask.get("target_object", ""),
                "from": "",
                "to": "",
                "parameters": {"risk_level": safety.get("risk_level")},
                "reason": safety.get("reason", "Safety veto blocked action."),
            }
        else:
            command = {
                "command": "MOVE_TO",
                "object_id": subtask.get("target_object", ""),
                "from": "input_rack",
                "to": subtask.get("destination", "safe_tray"),
                "parameters": {
                    "speed": "slow" if safety.get("risk_level") != "low" else "normal",
                    "route": "around_hazard" if safety.get("risk_level") == "medium" else "direct",
                },
                "reason": subtask.get("goal", "Execute safe movement."),
            }
        prompt = f"Subtask: {subtask}\nSafety: {safety}\nLocalizer: {localizer}"
        llm = run_json(agent_name=self.name, system_prompt=SYSTEM, user_prompt=prompt, fallback_json=command)
        return from_llm(
            self.name,
            llm,
            summary=f"Planned command: {llm.json.get('command', 'NONE')}",
            confidence=0.9,
        )


motion_planner_agent = MotionPlannerAgent()