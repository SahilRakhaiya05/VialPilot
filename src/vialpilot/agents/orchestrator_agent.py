"""Orchestrator agent — delegates to workflow service for API compatibility."""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.vialpilot.db import repository as repo
from src.vialpilot.services.workflow import execute_run


def run_swarm(
    instruction: str,
    scene_id: str = "safe_sorting_scene",
    image_bytes: Optional[bytes] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Legacy entry point; prefer workflow.execute_run via API."""
    if db is None:
        from src.vialpilot.db.database import SessionLocal

        db = SessionLocal()
        try:
            run = repo.create_run(db, instruction, scene_id)
            if image_bytes:
                from src.vialpilot.config import UPLOAD_DIR

                path = UPLOAD_DIR / run.id / "inline_upload.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(image_bytes)
                repo.update_run(db, run, upload_paths=[str(path)], status="uploaded")
            execute_run(db, run)
            db.commit()
            detail = repo.to_run_detail(run)
            return {
                "instruction": detail.instruction,
                "scene_id": detail.scene_id,
                "timeline": detail.agent_outputs,
                "bench": detail.bench_state,
                "notebook": detail.final_report,
                "metrics": detail.latency_metrics,
                "run_id": detail.run_id,
            }
        finally:
            db.close()

    run = repo.create_run(db, instruction, scene_id)
    execute_run(db, run)
    detail = repo.to_run_detail(run)
    return detail.model_dump()