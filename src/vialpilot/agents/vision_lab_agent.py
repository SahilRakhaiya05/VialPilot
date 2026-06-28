from __future__ import annotations

from typing import Any, Dict, Optional

from src.vialpilot.agents.base import from_llm
from src.vialpilot.llm.client import run_json
from src.vialpilot.models.schemas import AgentOutput

SYSTEM = """You are the Vision Lab Agent for VialPilot on a physical lab bench.
Analyze the image and identify sample vials, trays, racks, hazard zones, and contamination areas.
Return JSON: {"objects":[{"id":"","label":"","color":"","zone":"","x":0,"y":0,"confidence":0.0,"bbox":{"x":0,"y":0,"w":0,"h":0}}],"zones":[],"hazards":[],"uncertainties":[],"visual_summary":""}"""


class VisionLabAgent:
    name = "VisionLabAgent"

    def run(
        self,
        instruction: str,
        scene_state: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png",
    ) -> AgentOutput:
        objects = []
        for obj in scene_state.get("objects", []):
            o = dict(obj)
            x, y = o.get("x", 0), o.get("y", 0)
            o.setdefault("bbox", {"x": x * 40, "y": y * 40, "w": 36, "h": 36})
            objects.append(o)
        fallback = {
            "objects": objects,
            "zones": scene_state.get("zones", []),
            "hazards": scene_state.get("hazards", []),
            "uncertainties": [o for o in scene_state.get("objects", []) if o.get("confidence", 1) < 0.7],
            "visual_summary": scene_state.get("description", "Lab bench scene analyzed."),
        }
        if not fallback["objects"]:
            fallback["visual_summary"] = "No objects detected in scene."
        prompt = f"Instruction: {instruction}\nKnown state: {scene_state}\nAnalyze lab-bench evidence."
        llm = run_json(
            agent_name=self.name,
            system_prompt=SYSTEM,
            user_prompt=prompt,
            fallback_json=fallback,
            image_bytes=image_bytes,
            image_mime=image_mime,
        )
        obj_count = len(llm.json.get("objects", []))
        return from_llm(
            self.name,
            llm,
            summary=f"Detected {obj_count} object(s) in lab scene.",
            confidence=0.85 if obj_count else 0.3,
        )


vision_lab_agent = VisionLabAgent()