"""Simple deterministic lab-bench simulator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from src.vialpilot.simulator.scenes import get_scene


@dataclass
class LabBench:
    state: Dict[str, Any]
    history: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_scene(cls, scene_id: str) -> "LabBench":
        return cls(state=get_scene(scene_id))

    def object_by_id(self, object_id: str) -> Optional[Dict[str, Any]]:
        for obj in self.state.get("objects", []):
            if obj.get("id") == object_id:
                return obj
        return None

    def zone_by_id(self, zone_id: str) -> Optional[Dict[str, Any]]:
        for zone in self.state.get("zones", []):
            if zone.get("id") == zone_id:
                return zone
        return None

    def apply_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        name = command.get("command")
        object_id = command.get("object_id")
        to_zone = command.get("to") or command.get("destination")
        result = {"applied": False, "message": "No action taken", "command": command}

        if name in {"REQUEST_HUMAN_CONFIRMATION", "REJECT_ACTION", "WAIT", "SCAN_AREA"}:
            result = {"applied": False, "message": f"{name}: {command.get('reason', '')}", "command": command}
        elif name in {"PICK_OBJECT", "PLACE_OBJECT", "MOVE_TO"} and object_id and to_zone:
            obj = self.object_by_id(object_id)
            zone = self.zone_by_id(to_zone)
            if obj and zone:
                obj["zone"] = zone["id"]
                obj["x"] = zone["x"] + max(0, zone["w"] // 2)
                obj["y"] = zone["y"] + max(0, zone["h"] // 2)
                obj["state"] = "moved"
                result = {"applied": True, "message": f"Moved {object_id} to {to_zone}", "command": command}
            else:
                result = {"applied": False, "message": "Object or target zone not found", "command": command}
        elif name == "COMPLETE_TASK":
            result = {"applied": True, "message": "Task marked complete", "command": command}

        self.history.append(result)
        return result

    def serialize(self) -> Dict[str, Any]:
        return {"state": self.state, "history": self.history}
