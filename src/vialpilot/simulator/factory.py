"""Simulator factory: VialPilot robotics lab or 2D lab bench."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union

from src.vialpilot.config import SIMULATOR_MODE
from src.vialpilot.simulator.lab_bench import LabBench
from src.vialpilot.simulator.session import SimulatorSession, get_session


def create_simulator(scene_id: str) -> Tuple[str, Union[LabBench, SimulatorSession]]:
    mode = SIMULATOR_MODE.lower()
    if mode in ("auto", "robot"):
        session = get_session(scene_id=scene_id)
        if session.available:
            session.reset(scene_id)
            return session.mode, session
        if mode == "lab_bench":
            pass
        return session.mode, session
    return "lab_bench", LabBench.from_scene(scene_id)


def get_vision_input(
    simulator: Union[LabBench, SimulatorSession],
    scene_id: str,
    upload_image: Optional[bytes],
) -> Tuple[Optional[bytes], Dict[str, Any]]:
    if isinstance(simulator, SimulatorSession):
        frame, state = simulator.observation_for_vision()
        return frame if not upload_image else upload_image, state
    bench = simulator if isinstance(simulator, LabBench) else LabBench.from_scene(scene_id)
    return upload_image, bench.state