from __future__ import annotations

from typing import Any, Dict, List

from src.vialpilot.agents.base import local_output
from src.vialpilot.llm.client import get_active_provider
from src.vialpilot.models.schemas import AgentOutput


class LabNotebookAgent:
    name = "LabNotebookAgent"

    def run(
        self,
        instruction: str,
        scene_name: str,
        agent_outputs: List[Dict[str, Any]],
        final_state: Dict[str, Any],
    ) -> AgentOutput:
        verified = sum(
            1
            for o in agent_outputs
            if o.get("agent_name") == "ReflectorAgent" and o.get("data", {}).get("success")
        )
        blocked = sum(
            1
            for o in agent_outputs
            if o.get("agent_name") == "SafetyVetoAgent" and o.get("status") == "blocked"
        )
        total_latency = sum(o.get("latency_ms", 0) for o in agent_outputs)
        data = {
            "project": "VialPilot",
            "scene": scene_name,
            "instruction": instruction,
            "actions_verified": verified,
            "safety_blocks": blocked,
            "llm_provider": get_active_provider(),
            "total_latency_ms": round(total_latency, 2),
            "final_summary": f"Completed {verified} verified action(s) with {blocked} safety block(s).",
            "final_state": final_state,
        }
        return local_output(
            self.name,
            data=data,
            summary=data["final_summary"],
            confidence=0.95,
        )


lab_notebook_agent = LabNotebookAgent()