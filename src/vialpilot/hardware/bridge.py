"""Hardware command bridge: robot simulator, MQTT, or webhook."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Union

import httpx

from src.vialpilot.config import HARDWARE_MODE, MQTT_BROKER_URL, WEBHOOK_COMMAND_URL
from src.vialpilot.simulator.lab_bench import LabBench
from src.vialpilot.simulator.session import SimulatorSession

logger = logging.getLogger(__name__)

VALID_COMMANDS = {
    "PICK_OBJECT",
    "PLACE_OBJECT",
    "MOVE_TO",
    "SCAN_AREA",
    "WAIT",
    "REQUEST_HUMAN_CONFIRMATION",
    "COMPLETE_TASK",
    "ABORT_TASK",
}


class HardwareBridge:
    def __init__(self, mode: Optional[str] = None) -> None:
        self.mode = (mode or HARDWARE_MODE).lower()

    def dispatch(
        self,
        command: Dict[str, Any],
        bench: Optional[LabBench] = None,
        robot: Optional[SimulatorSession] = None,
        simulator_mode: str = "lab_bench",
    ) -> Dict[str, Any]:
        name = command.get("command", "")
        if name not in VALID_COMMANDS:
            return {
                "applied": False,
                "message": f"Unknown command: {name}",
                "command": command,
                "bridge_mode": self.mode,
            }

        if self.mode == "mqtt":
            return self._dispatch_mqtt(command)
        if self.mode == "webhook":
            return self._dispatch_webhook(command)
        if robot and simulator_mode in ("pybullet-real", "software-robot"):
            return robot.apply_command(command)
        return self._dispatch_simulation(command, bench)

    def _dispatch_simulation(self, command: Dict[str, Any], bench: Optional[LabBench]) -> Dict[str, Any]:
        if bench is None:
            return {
                "applied": False,
                "message": "No simulator bench available",
                "command": command,
                "bridge_mode": "simulation",
            }
        result = bench.apply_command(command)
        result["bridge_mode"] = "simulation"
        return result

    def _dispatch_mqtt(self, command: Dict[str, Any]) -> Dict[str, Any]:
        if not MQTT_BROKER_URL:
            return {
                "applied": False,
                "message": "MQTT_BROKER_URL not configured",
                "command": command,
                "bridge_mode": "mqtt",
            }
        try:
            import paho.mqtt.publish as publish

            publish.single(
                "vialpilot/robot/command",
                payload=json.dumps(command),
                hostname=MQTT_BROKER_URL.replace("mqtt://", "").split(":")[0],
            )
            return {
                "applied": True,
                "message": "Command published to vialpilot/robot/command",
                "command": command,
                "bridge_mode": "mqtt",
            }
        except Exception as exc:
            logger.error("MQTT dispatch failed: %s", exc)
            return {
                "applied": False,
                "message": f"MQTT error: {exc}",
                "command": command,
                "bridge_mode": "mqtt",
            }

    def _dispatch_webhook(self, command: Dict[str, Any]) -> Dict[str, Any]:
        if not WEBHOOK_COMMAND_URL:
            return {
                "applied": False,
                "message": "WEBHOOK_COMMAND_URL not configured",
                "command": command,
                "bridge_mode": "webhook",
            }
        try:
            response = httpx.post(WEBHOOK_COMMAND_URL, json=command, timeout=10.0)
            response.raise_for_status()
            return {
                "applied": True,
                "message": f"Webhook accepted ({response.status_code})",
                "command": command,
                "bridge_mode": "webhook",
            }
        except Exception as exc:
            logger.error("Webhook dispatch failed: %s", exc)
            return {
                "applied": False,
                "message": f"Webhook error: {exc}",
                "command": command,
                "bridge_mode": "webhook",
            }


bridge = HardwareBridge()