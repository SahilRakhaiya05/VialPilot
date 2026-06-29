"""SQLAlchemy ORM models for persistent storage."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text

from src.vialpilot.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunRecord(Base):
    __tablename__ = "runs"

    id = Column(String(36), primary_key=True)
    instruction = Column(Text, nullable=False)
    scene_id = Column(String(64), default="safe_sorting_scene")
    status = Column(String(32), default="created")
    upload_paths = Column(JSON, default=list)
    frame_paths = Column(JSON, default=list)
    visual_observations = Column(JSON, nullable=True)
    agent_outputs = Column(JSON, default=list)
    safety_decisions = Column(JSON, default=list)
    commands = Column(JSON, default=list)
    latency_metrics = Column(JSON, default=dict)
    final_report = Column(JSON, nullable=True)
    bench_state = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    run_meta = Column(JSON, default=dict)
    current_agent = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class RunEventRecord(Base):
    __tablename__ = "run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    agent_name = Column(String(64), nullable=True)
    message = Column(Text, default="")
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_utcnow)


class AgentOutputRecord(Base):
    __tablename__ = "agent_outputs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(64), nullable=False)
    status = Column(String(32), default="success")
    summary = Column(Text, default="")
    confidence = Column(Float, default=0.0)
    data = Column(JSON, default=dict)
    latency_ms = Column(Float, default=0.0)
    mode = Column(String(16), default="unavailable")
    created_at = Column(DateTime, default=_utcnow)