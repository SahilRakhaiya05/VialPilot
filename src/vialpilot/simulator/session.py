"""Unified VialPilot robotics simulator session."""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional, Tuple

from src.vialpilot.config import ROBOT_TASK_NAME, SIMULATOR_MODE
from src.vialpilot.simulator.software_robot import SoftwareRobotBackend

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_session: Optional["SimulatorSession"] = None


class SimulatorSession:
    """VialPilot precision lab simulator — software robotics engine."""

    def __init__(
        self,
        task_name: str = ROBOT_TASK_NAME,
        *,
        scene_id: str = "safe_sorting_scene",
        prefer: Optional[str] = None,
    ) -> None:
        self.task_name = task_name
        self.scene_id = scene_id
        self.backend = SoftwareRobotBackend(scene_id)
        self.mode = "software-robot"
        _ = prefer  # legacy compat

    @property
    def available(self) -> bool:
        return self.backend.available

    def reset(self, scene_id: Optional[str] = None) -> None:
        if scene_id:
            self.scene_id = scene_id
        self.backend.reset(scene_id)

    def get_frame_png(self) -> bytes:
        return self.backend.get_frame_png()

    def observation_for_vision(self) -> Tuple[bytes, Dict[str, Any]]:
        return self.backend.observation_for_vision()

    def apply_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        return self.backend.apply_command(command)

    def get_scene_state(self) -> Dict[str, Any]:
        return self.backend.get_scene_state()

    def status(self) -> Dict[str, Any]:
        base = self.backend.status()
        base["session_mode"] = self.mode
        base["simulator_mode"] = SIMULATOR_MODE
        return base


def get_session(
    force_new: bool = False,
    *,
    task_name: Optional[str] = None,
    scene_id: str = "safe_sorting_scene",
    display_gui: Optional[bool] = None,
) -> SimulatorSession:
    global _session
    _ = display_gui  # legacy compat
    with _lock:
        if force_new or _session is None:
            _session = SimulatorSession(
                task_name or ROBOT_TASK_NAME,
                scene_id=scene_id,
            )
        return _session