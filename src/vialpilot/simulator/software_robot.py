"""VialPilot software robot simulator — works without PyBullet (Windows-friendly)."""
from __future__ import annotations

import copy
import logging
import math
from typing import Any, Dict, Optional, Tuple

from src.vialpilot.config import ROBOT_OBS_DIR
from src.vialpilot.simulator.robot_renderer import render_frame, scene_for_vision
from src.vialpilot.simulator.scenes import get_scene

logger = logging.getLogger(__name__)


ARM_BASE_X = -0.42
ARM_BASE_Z = 0.15


class SoftwareRobotBackend:
    """Deterministic VialPilot robotics lab with rendered camera frames."""

    def __init__(self, scene_id: str = "safe_sorting_scene") -> None:
        self.scene_id = scene_id
        self.scene = copy.deepcopy(get_scene(scene_id))
        self.scene["name"] = self.scene.get("name", scene_id)
        bench = self.scene.get("bench_size", {"width": 10, "height": 6})
        self.arm_pos = (bench["width"] / 2, bench["height"] / 2)
        self.gripper_open = True
        self.holding: Optional[str] = None
        self.step_count = 0
        self.last_prompt = (
            f"Put the sample objects into the correct trays on the {self.scene['name']} bench."
        )
        self.mode = "software-robot"
        ROBOT_OBS_DIR.mkdir(parents=True, exist_ok=True)
        self._save_frame()

    @property
    def available(self) -> bool:
        return True

    def reset(self, scene_id: Optional[str] = None) -> None:
        if scene_id:
            self.scene_id = scene_id
        self.scene = copy.deepcopy(get_scene(self.scene_id))
        bench = self.scene.get("bench_size", {"width": 10, "height": 6})
        self.arm_pos = (bench["width"] / 2, bench["height"] / 2)
        self.gripper_open = True
        self.holding = None
        self.step_count = 0
        self._save_frame()

    def _arm_reach_norm(self) -> float:
        bx, _ = self.arm_pos
        bw = self.scene.get("bench_size", {}).get("width", 10)
        return max(0.0, min(1.0, bx / bw))

    def _bench_to_world(self, x: float, y: float) -> Tuple[float, float]:
        bench = self.scene.get("bench_size", {"width": 10, "height": 6})
        bw, bh = bench["width"], bench["height"]
        wx = (x / bw - 0.5) * 1.0
        wz = -(y / bh - 0.5) * 0.65
        return wx, wz

    def _joints_for_target(self, tx: float, tz: float) -> Tuple[float, float, float]:
        dx = tx - ARM_BASE_X
        dz = tz - ARM_BASE_Z
        j1 = math.atan2(dx, dz)
        dist = math.sqrt(dx * dx + dz * dz)
        j2 = -0.55 - min(dist * 1.2, 0.85)
        j3 = 0.25
        return j1, j2, j3

    def _save_frame(self) -> bytes:
        png = render_frame(
            self.scene,
            arm_pos=(self._arm_reach_norm(), 0.12),
            gripper_open=self.gripper_open,
            holding_object_id=self.holding,
        )
        (ROBOT_OBS_DIR / "latest_frame.png").write_bytes(png)
        return png

    def get_frame_png(self) -> bytes:
        return self._save_frame()

    def observation_for_vision(self) -> Tuple[bytes, Dict[str, Any]]:
        frame = self.get_frame_png()
        state = scene_for_vision(self.scene)
        state["prompt"] = self.last_prompt
        state["scene_id"] = self.scene_id
        return frame, state

    def apply_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        name = command.get("command", "")
        object_id = command.get("object_id")
        to_zone = command.get("to") or command.get("destination")
        self.step_count += 1

        if name in {"WAIT", "SCAN_AREA", "REQUEST_HUMAN_CONFIRMATION"}:
            return {
                "applied": False,
                "message": f"{name}: {command.get('reason', 'skipped')}",
                "command": command,
                "bridge_mode": "software-robot",
            }

        if name == "PICK_OBJECT" and object_id:
            obj = next((o for o in self.scene["objects"] if o["id"] == object_id), None)
            if obj:
                self.arm_pos = (obj["x"], obj["y"])
                self.gripper_open = False
                self.holding = object_id
                self._save_frame()
                return {
                    "applied": True,
                    "message": f"Robot picked {object_id}",
                    "command": command,
                    "bridge_mode": "software-robot",
                }

        if name in {"PLACE_OBJECT", "MOVE_TO"} and object_id and to_zone:
            obj = next((o for o in self.scene["objects"] if o["id"] == object_id), None)
            zone = next((z for z in self.scene["zones"] if z["id"] == to_zone), None)
            if obj and zone:
                self.arm_pos = (zone["x"] + zone["w"] / 2, zone["y"] + zone["h"] / 2)
                obj["zone"] = zone["id"]
                obj["x"] = zone["x"] + zone["w"] / 2
                obj["y"] = zone["y"] + zone["h"] / 2
                obj["state"] = "moved"
                self.gripper_open = True
                self.holding = None
                self._save_frame()
                return {
                    "applied": True,
                    "message": f"Robot moved {object_id} → {to_zone}",
                    "command": command,
                    "bridge_mode": "software-robot",
                }
            return {
                "applied": False,
                "message": "Object or zone not found",
                "command": command,
                "bridge_mode": "software-robot",
            }

        if name == "COMPLETE_TASK":
            self._save_frame()
            return {"applied": True, "message": "Task complete", "command": command, "bridge_mode": "software-robot"}

        return {"applied": False, "message": "Unknown command", "command": command, "bridge_mode": "software-robot"}

    def serialize(self) -> Dict[str, Any]:
        return copy.deepcopy(self.scene)

    def get_scene_state(self) -> Dict[str, Any]:
        """Full 3D scene state for the WebGL robotics viewer."""
        bx, by = self.arm_pos
        tx, tz = self._bench_to_world(bx, by)
        j1, j2, j3 = self._joints_for_target(tx, tz)
        desc = self.scene.get("description", "")
        prompt = desc or self.last_prompt
        return {
            "scene_id": self.scene_id,
            "scene": self.serialize(),
            "arm": {
                "target": {"x": tx, "y": 0.42, "z": tz},
                "gripper_open": self.gripper_open,
                "holding": self.holding,
                "joints": [j1, j2, j3, 0.0, 0.0, 0.0],
            },
            "task_prompt": prompt,
            "step_count": self.step_count,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "available": True,
            "mode": self.mode,
            "scene_id": self.scene_id,
            "task_name": "visual_manipulation",
            "last_prompt": self.last_prompt,
            "step_count": self.step_count,
            "backend": "VialPilot 3D Robot Simulator",
            "pybullet": False,
            "physics_engine": "webgl",
            "objects": len(self.scene.get("objects", [])),
        }