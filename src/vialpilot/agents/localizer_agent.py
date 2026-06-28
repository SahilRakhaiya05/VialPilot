from __future__ import annotations

from typing import Any, Dict

from src.vialpilot.agents.base import from_llm
from src.vialpilot.llm.client import run_json
from src.vialpilot.models.schemas import AgentOutput

SYSTEM = """You are the Localizer Agent. Map visual objects to simulator coordinates.
Return JSON: {"object_locations":[{"object_id":"","label":"","position":{"x":0,"y":0},"confidence":0.0}]}"""


class LocalizerAgent:
    name = "LocalizerAgent"

    def run(self, vision: Dict[str, Any]) -> AgentOutput:
        locations = [
            {
                "object_id": obj.get("id"),
                "label": obj.get("label"),
                "position": {"x": obj.get("x", 0), "y": obj.get("y", 0)},
                "confidence": obj.get("confidence", 0.9),
            }
            for obj in vision.get("objects", [])
        ]
        fallback = {"object_locations": locations}
        prompt = f"Vision: {vision}\nReturn object locations."
        llm = run_json(agent_name=self.name, system_prompt=SYSTEM, user_prompt=prompt, fallback_json=fallback)
        return from_llm(
            self.name,
            llm,
            summary=f"Localized {len(locations)} object(s).",
            confidence=0.88 if locations else 0.2,
        )


localizer_agent = LocalizerAgent()