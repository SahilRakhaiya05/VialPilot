from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.vialpilot.agents.base import from_llm
from src.vialpilot.llm.client import run_json
from src.vialpilot.llm.images import ImageFrame, normalize_frames
from src.vialpilot.models.schemas import AgentOutput

SYSTEM = """You are the Vision Lab Agent for VialPilot on a physical lab bench.
Analyze the image(s) and identify sample vials, trays, racks, hazard zones, and contamination areas.
When multiple frames are provided (video sequence), track motion and consistency across time.
Return JSON: {"objects":[{"id":"","label":"","color":"","zone":"","x":0,"y":0,"confidence":0.0,"bbox":{"x":0,"y":0,"w":0,"h":0}}],"zones":[],"hazards":[],"uncertainties":[],"visual_summary":"","frame_count":1}"""


class VisionLabAgent:
    name = "VisionLabAgent"

    def run(
        self,
        instruction: str,
        scene_state: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png",
        frames: Optional[List[ImageFrame]] = None,
    ) -> AgentOutput:
        objects = []
        for obj in scene_state.get("objects", []):
            o = dict(obj)
            x, y = o.get("x", 0), o.get("y", 0)
            o.setdefault("bbox", {"x": x * 40, "y": y * 40, "w": 36, "h": 36})
            objects.append(o)
        frame_list = normalize_frames(image_bytes, image_mime, frames)
        fallback = {
            "objects": objects,
            "zones": scene_state.get("zones", []),
            "hazards": scene_state.get("hazards", []),
            "uncertainties": [o for o in scene_state.get("objects", []) if o.get("confidence", 1) < 0.7],
            "visual_summary": scene_state.get("description", "Lab bench scene analyzed."),
            "frame_count": len(frame_list) or 1,
        }
        if not fallback["objects"]:
            fallback["visual_summary"] = "No objects detected in scene."
        frame_note = ""
        if len(frame_list) > 1:
            frame_note = f"\nYou are given {len(frame_list)} sequential video frames — fuse evidence across time."
        prompt = (
            f"Instruction: {instruction}\nKnown state: {scene_state}\n"
            f"Analyze lab-bench evidence.{frame_note}"
        )
        llm = run_json(
            agent_name=self.name,
            system_prompt=SYSTEM,
            user_prompt=prompt,
            fallback_json=fallback,
            images=frame_list or None,
            image_bytes=image_bytes if not frame_list else None,
            image_mime=image_mime,
        )
        llm.json.setdefault("frame_count", len(frame_list) or 1)
        obj_count = len(llm.json.get("objects", []))
        summary = f"Detected {obj_count} object(s)"
        if len(frame_list) > 1:
            summary += f" across {len(frame_list)} video frames"
        summary += "."
        return from_llm(
            self.name,
            llm,
            summary=summary,
            confidence=0.85 if obj_count else 0.3,
        )


vision_lab_agent = VisionLabAgent()