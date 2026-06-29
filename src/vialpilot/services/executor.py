"""Background workflow executor for live UI updates."""
from __future__ import annotations

import logging
import threading
from typing import Set

from src.vialpilot.db.database import SessionLocal
from src.vialpilot.db import repository as repo
from src.vialpilot.services.workflow import execute_run

logger = logging.getLogger(__name__)

_running: Set[str] = set()
_lock = threading.Lock()


def is_running(run_id: str) -> bool:
    with _lock:
        return run_id in _running


def execute_async(run_id: str) -> bool:
    """Start workflow in background. Returns False if already running."""
    with _lock:
        if run_id in _running:
            return False
        _running.add(run_id)

    def _worker() -> None:
        db = SessionLocal()
        try:
            run = repo.get_run(db, run_id)
            if run:
                execute_run(db, run, commit_each_step=True)
                db.commit()
        except Exception:
            logger.exception("Background execution failed for %s", run_id)
            db.rollback()
        finally:
            db.close()
            with _lock:
                _running.discard(run_id)

    threading.Thread(target=_worker, daemon=True).start()
    return True