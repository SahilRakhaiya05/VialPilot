"""FastAPI route handlers."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from src.vialpilot.agents.localizer_agent import localizer_agent
from src.vialpilot.agents.motion_planner_agent import motion_planner_agent
from src.vialpilot.agents.reflector_agent import reflector_agent
from src.vialpilot.agents.safety_veto_agent import safety_veto_agent
from src.vialpilot.agents.task_decomposer_agent import task_decomposer_agent
from src.vialpilot.agents.vision_lab_agent import vision_lab_agent
from src.vialpilot.config import APP_MODE, CEREBRAS_MODEL, GEMINI_MODEL, HARDWARE_MODE
from src.vialpilot.db import repository as repo
from src.vialpilot.db.database import get_db_session
from src.vialpilot.llm.client import get_active_model, get_active_provider, get_provider_status
from src.vialpilot.models.schemas import (
    ConfirmRequest,
    AgentDecomposeRequest,
    AgentPlanRequest,
    AgentReflectRequest,
    AgentSafetyRequest,
    AgentVisionRequest,
    CreateRunRequest,
    CreateRunResponse,
    ExecuteResponse,
    HealthResponse,
    SettingsResponse,
    RunDetail,
    RunEvent,
    RunSummary,
    UploadResponse,
)
from src.vialpilot.services.files import FileServiceError, extract_video_frames, save_upload
from src.vialpilot.services.reports import report_to_json, report_to_markdown
from src.vialpilot.integrations.run_to_log import run_to_log_text
from src.vialpilot.services.executor import execute_async, is_running

from src.vialpilot.services.workflow import execute_run

router = APIRouter(prefix="/api")


@router.get("/models/cerebras")
def cerebras_models():
    """List Gemma 4 model info from Cerebras (public catalog + resolved id)."""
    from src.vialpilot.llm.cerebras_models import GEMMA4_DEFAULT_MODEL, fetch_public_model_info
    from src.vialpilot.llm.client import _cerebras_client

    cerebras = _cerebras_client()
    info = fetch_public_model_info(GEMMA4_DEFAULT_MODEL)
    return {
        "default_model": GEMMA4_DEFAULT_MODEL,
        "resolved_model": cerebras.model if cerebras.enabled else GEMMA4_DEFAULT_MODEL,
        "api_key_configured": cerebras.enabled,
        "catalog": info,
    }


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    provider = get_active_provider()
    model = get_active_model()
    return HealthResponse(
        status="ok",
        app_mode=APP_MODE,
        llm_provider=provider,
        llm_mode="real" if provider != "mock" else "mock",
        database="connected",
        hardware_mode=HARDWARE_MODE,
        model=model,
    )


@router.get("/settings", response_model=SettingsResponse)
def settings() -> SettingsResponse:
    provider = get_active_provider()
    return SettingsResponse(
        app_mode=APP_MODE,
        active_provider=provider,
        llm_mode="real" if provider != "mock" else "mock",
        hardware_mode=HARDWARE_MODE,
        providers=get_provider_status(),
        cerebras_model=get_active_model() if "cerebras" in get_active_provider() else CEREBRAS_MODEL,
        gemini_model=GEMINI_MODEL,
    )


@router.post("/runs", response_model=CreateRunResponse)
def create_run(body: CreateRunRequest, db: Session = Depends(get_db_session)) -> CreateRunResponse:
    run = repo.create_run(db, body.instruction, body.scene_id)
    return CreateRunResponse(run_id=run.id, status=run.status, created_at=run.created_at)


@router.get("/runs", response_model=List[RunSummary])
def list_runs(db: Session = Depends(get_db_session)) -> List[RunSummary]:
    return [repo.to_run_summary(r) for r in repo.list_runs(db)]


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str, db: Session = Depends(get_db_session)) -> RunDetail:
    run = repo.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return repo.to_run_detail(run)


@router.post("/runs/{run_id}/upload", response_model=UploadResponse)
async def upload_files(
    run_id: str,
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db_session),
) -> UploadResponse:
    run = repo.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")

    if not image and not video:
        raise HTTPException(400, "Provide image and/or video file")

    paths = list(run.upload_paths or [])
    frame_paths = list(run.frame_paths or [])

    try:
        if image and image.filename:
            path, _ = await save_upload(run_id, image)
            paths.append(path)
        if video and video.filename:
            path, _ = await save_upload(run_id, video)
            paths.append(path)
            frame_paths = extract_video_frames(path, run_id)
    except FileServiceError as exc:
        raise HTTPException(400, str(exc)) from exc

    repo.update_run(db, run, upload_paths=paths, frame_paths=frame_paths, status="uploaded")
    repo.add_event(db, run_id, "files_uploaded", message=f"Uploaded {len(paths)} file(s)")
    return UploadResponse(
        run_id=run_id,
        files=paths,
        frame_paths=frame_paths,
        message="Upload successful",
    )


@router.post("/runs/{run_id}/execute", response_model=ExecuteResponse)
def execute(run_id: str, background: bool = True, db: Session = Depends(get_db_session)) -> ExecuteResponse:
    run = repo.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if is_running(run_id) or run.status == "running":
        return ExecuteResponse(run_id=run_id, status="running", message="Already running")
    if background:
        repo.update_run(db, run, status="running", current_agent="Orchestrator")
        if not execute_async(run_id):
            raise HTTPException(409, "Run already executing")
        return ExecuteResponse(run_id=run_id, status="running", message="Workflow started — poll for live updates")
    execute_run(db, run, commit_each_step=False)
    run = repo.get_run(db, run_id)
    return ExecuteResponse(run_id=run_id, status=run.status, message=f"Execution finished: {run.status}")


@router.post("/runs/{run_id}/rerun", response_model=ExecuteResponse)
def rerun_workflow(run_id: str, background: bool = True, db: Session = Depends(get_db_session)) -> ExecuteResponse:
    """Clear outputs and re-execute with live AI."""
    run = repo.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if is_running(run_id):
        return ExecuteResponse(run_id=run_id, status="running", message="Already running")
    repo.update_run(
        db,
        run,
        status="uploaded",
        current_agent=None,
        error_message=None,
        agent_outputs=[],
        safety_decisions=[],
        commands=[],
        bench_state=None,
        visual_observations=None,
        latency_metrics={},
        final_report=None,
    )
    repo.add_event(db, run_id, "workflow_rerun", message="Re-running workflow with live AI")
    if background:
        repo.update_run(db, run, status="running", current_agent="Orchestrator")
        if not execute_async(run_id):
            raise HTTPException(409, "Run already executing")
        return ExecuteResponse(run_id=run_id, status="running", message="Live AI workflow started")
    execute_run(db, run, commit_each_step=False)
    run = repo.get_run(db, run_id)
    return ExecuteResponse(run_id=run_id, status=run.status, message=f"Re-run finished: {run.status}")


@router.post("/runs/{run_id}/confirm", response_model=ExecuteResponse)
def confirm_human(run_id: str, body: ConfirmRequest, db: Session = Depends(get_db_session)) -> ExecuteResponse:
    run = repo.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    meta = dict(run.run_meta or {})
    meta["human_confirmed"] = body.confirmed
    meta["confirmation_note"] = body.note
    repo.update_run(db, run, run_meta=meta, status="uploaded")
    repo.add_event(db, run_id, "human_confirmed", message=body.note or "Operator confirmed action")
    if body.confirmed:
        execute_async(run_id)
        return ExecuteResponse(run_id=run_id, status="running", message="Re-running with human confirmation")
    return ExecuteResponse(run_id=run_id, status=run.status, message="Confirmation declined")


@router.get("/runs/{run_id}/events", response_model=List[RunEvent])
def get_events(run_id: str, db: Session = Depends(get_db_session)) -> List[RunEvent]:
    run = repo.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return [repo.to_run_event(e) for e in repo.list_events(db, run_id)]


@router.get("/runs/{run_id}/pipeline-logs")
def pipeline_logs(run_id: str, db: Session = Depends(get_db_session)):
    """Export run as NDJSON for the Pipeline Analyzer."""
    run = repo.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    events = [
        {
            "created_at": e.created_at,
            "event_type": e.event_type,
            "agent_name": e.agent_name,
            "message": e.message,
            "payload": e.payload or {},
        }
        for e in repo.list_events(db, run_id)
    ]
    text = run_to_log_text(
        run_id=run_id,
        instruction=run.instruction,
        events=events,
        agent_outputs=run.agent_outputs,
    )
    return PlainTextResponse(text, media_type="application/x-ndjson")


@router.get("/runs/{run_id}/report")
def get_report(run_id: str, format: str = "json", db: Session = Depends(get_db_session)):
    run = repo.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if not run.final_report and run.status in ("completed", "blocked", "failed"):
        run.final_report = __import__("src.vialpilot.services.reports", fromlist=["build_report"]).build_report(run)
    if format == "markdown":
        return PlainTextResponse(report_to_markdown(run), media_type="text/markdown")
    return Response(report_to_json(run), media_type="application/json")


@router.post("/agent/vision")
def agent_vision(body: AgentVisionRequest):
    from src.vialpilot.services.files import read_image_bytes, image_mime_for_path

    image_bytes = None
    mime = "image/png"
    if body.image_path:
        image_bytes = read_image_bytes(body.image_path)
        mime = image_mime_for_path(body.image_path)
    return vision_lab_agent.run(body.instruction, body.scene_state, image_bytes, mime)


@router.post("/agent/decompose")
def agent_decompose(body: AgentDecomposeRequest):
    return task_decomposer_agent.run(body.instruction, body.vision)


@router.post("/agent/safety")
def agent_safety(body: AgentSafetyRequest):
    return safety_veto_agent.run(body.subtask, body.vision, body.scene_state)


@router.post("/agent/plan")
def agent_plan(body: AgentPlanRequest):
    return motion_planner_agent.run(body.subtask, body.safety, body.localizer)


@router.post("/agent/reflect")
def agent_reflect(body: AgentReflectRequest):
    return reflector_agent.run(body.subtask, body.actor_result, body.scene_state)