"""Robot simulator API — VialPilot precision lab."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from src.vialpilot.config import ROBOT_TASK_NAME
from src.vialpilot.simulator.session import get_session

router = APIRouter(prefix="/simulator", tags=["simulator"])


class SimulatorInitRequest(BaseModel):
    task_name: Optional[str] = None
    scene_id: str = "safe_sorting_scene"
    display_gui: bool = False
    force_new: bool = False


@router.get("/status")
def simulator_status():
    return get_session().status()


@router.get("/scene")
def simulator_scene():
    """Full 3D scene JSON for the WebGL robotics viewer."""
    return get_session().get_scene_state()


@router.post("/init")
def init_simulator(body: SimulatorInitRequest):
    session = get_session(
        force_new=body.force_new,
        task_name=body.task_name or ROBOT_TASK_NAME,
        scene_id=body.scene_id,
    )
    session.reset(body.scene_id)
    return session.status()


@router.get("/frame.png")
def simulator_frame():
    session = get_session()
    try:
        data = session.get_frame_png()
    except Exception as exc:
        raise HTTPException(503, f"Simulator frame unavailable: {exc}") from exc
    return Response(content=data, media_type="image/png")


@router.post("/step")
def simulator_step(command: dict):
    session = get_session()
    return session.apply_command(command)