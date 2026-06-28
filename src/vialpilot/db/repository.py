"""Database repository for runs, events, and agent outputs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.vialpilot.db.models import AgentOutputRecord, RunEventRecord, RunRecord
from src.vialpilot.models.schemas import AgentOutput, RunDetail, RunEvent, RunSummary


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_run(db: Session, instruction: str, scene_id: str = "safe_sorting_scene") -> RunRecord:
    run = RunRecord(
        id=str(uuid.uuid4()),
        instruction=instruction,
        scene_id=scene_id,
        status="created",
        upload_paths=[],
        frame_paths=[],
        agent_outputs=[],
        safety_decisions=[],
        commands=[],
        latency_metrics={},
    )
    db.add(run)
    db.flush()
    add_event(db, run.id, "run_created", message="Lab run created")
    return run


def get_run(db: Session, run_id: str) -> Optional[RunRecord]:
    return db.get(RunRecord, run_id)


def list_runs(db: Session, limit: int = 50) -> List[RunRecord]:
    return db.query(RunRecord).order_by(RunRecord.created_at.desc()).limit(limit).all()


def update_run(db: Session, run: RunRecord, **fields: Any) -> RunRecord:
    for key, value in fields.items():
        setattr(run, key, value)
    run.updated_at = _utcnow()
    db.flush()
    return run


def add_event(
    db: Session,
    run_id: str,
    event_type: str,
    *,
    agent_name: Optional[str] = None,
    message: str = "",
    payload: Optional[Dict[str, Any]] = None,
) -> RunEventRecord:
    event = RunEventRecord(
        run_id=run_id,
        event_type=event_type,
        agent_name=agent_name,
        message=message,
        payload=payload or {},
    )
    db.add(event)
    db.flush()
    return event


def list_events(db: Session, run_id: str) -> List[RunEventRecord]:
    return (
        db.query(RunEventRecord)
        .filter(RunEventRecord.run_id == run_id)
        .order_by(RunEventRecord.created_at.asc(), RunEventRecord.id.asc())
        .all()
    )


def save_agent_output(db: Session, run_id: str, output: AgentOutput) -> AgentOutputRecord:
    record = AgentOutputRecord(
        run_id=run_id,
        agent_name=output.agent_name,
        status=output.status,
        summary=output.summary,
        confidence=output.confidence,
        data=output.data,
        latency_ms=output.latency_ms,
        mode=output.mode,
    )
    db.add(record)
    db.flush()
    return record


def to_run_summary(run: RunRecord) -> RunSummary:
    uploads = run.upload_paths or []
    return RunSummary(
        run_id=run.id,
        instruction=run.instruction,
        status=run.status,
        scene_id=run.scene_id,
        created_at=run.created_at,
        updated_at=run.updated_at,
        has_image=any(p.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) for p in uploads),
        has_video=any(p.lower().endswith(".mp4") for p in uploads),
    )


def to_run_detail(run: RunRecord) -> RunDetail:
    summary = to_run_summary(run)
    outputs = [
        AgentOutput(
            agent_name=o.get("agent_name", ""),
            status=o.get("status", "success"),
            summary=o.get("summary", ""),
            confidence=o.get("confidence", 0.0),
            data=o.get("data", {}),
            latency_ms=o.get("latency_ms", 0.0),
            mode=o.get("mode", "mock"),
        )
        for o in (run.agent_outputs or [])
    ]
    return RunDetail(
        **summary.model_dump(),
        current_agent=run.current_agent,
        run_meta=run.run_meta or {},
        visual_observations=run.visual_observations,
        agent_outputs=outputs,
        safety_decisions=run.safety_decisions or [],
        commands=run.commands or [],
        latency_metrics=run.latency_metrics or {},
        final_report=run.final_report,
        bench_state=run.bench_state,
        upload_paths=run.upload_paths or [],
        frame_paths=run.frame_paths or [],
        error_message=run.error_message,
    )


def to_run_event(event: RunEventRecord) -> RunEvent:
    return RunEvent(
        id=event.id,
        run_id=event.run_id,
        event_type=event.event_type,
        agent_name=event.agent_name,
        message=event.message,
        payload=event.payload or {},
        created_at=event.created_at,
    )