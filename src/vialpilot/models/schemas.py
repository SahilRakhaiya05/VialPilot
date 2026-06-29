"""Pydantic request/response models for the VialPilot API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AgentStatus = Literal["success", "warning", "blocked", "failed"]
RunStatus = Literal["created", "uploaded", "running", "completed", "failed", "blocked"]
LLMMode = Literal["real", "unavailable"]


class AgentOutput(BaseModel):
    agent_name: str
    status: AgentStatus
    summary: str
    confidence: float = 0.0
    data: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    mode: LLMMode = "unavailable"


class LLMResult(BaseModel):
    mode: LLMMode
    model: str
    latency_ms: float
    raw_text: str
    result_json: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    @property
    def json(self) -> Dict[str, Any]:
        return self.result_json


class CreateRunRequest(BaseModel):
    instruction: str
    scene_id: str = "safe_sorting_scene"


class CreateRunResponse(BaseModel):
    run_id: str
    status: RunStatus
    created_at: datetime


class RunSummary(BaseModel):
    run_id: str
    instruction: str
    status: RunStatus
    scene_id: str
    created_at: datetime
    updated_at: datetime
    has_image: bool = False
    has_video: bool = False


class RunDetail(RunSummary):
    current_agent: Optional[str] = None
    run_meta: Dict[str, Any] = Field(default_factory=dict)
    visual_observations: Optional[Dict[str, Any]] = None
    agent_outputs: List[AgentOutput] = Field(default_factory=list)
    safety_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    commands: List[Dict[str, Any]] = Field(default_factory=list)
    latency_metrics: Dict[str, Any] = Field(default_factory=dict)
    final_report: Optional[Dict[str, Any]] = None
    bench_state: Optional[Dict[str, Any]] = None
    upload_paths: List[str] = Field(default_factory=list)
    frame_paths: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class RunEvent(BaseModel):
    id: int
    run_id: str
    event_type: str
    agent_name: Optional[str] = None
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ExecuteResponse(BaseModel):
    run_id: str
    status: RunStatus
    message: str


class UploadResponse(BaseModel):
    run_id: str
    files: List[str]
    frame_paths: List[str] = Field(default_factory=list)
    message: str


class HealthResponse(BaseModel):
    status: str
    app_mode: str
    llm_provider: str
    llm_mode: LLMMode
    database: str
    hardware_mode: str
    model: str = ""


class SettingsResponse(BaseModel):
    app_mode: str
    active_provider: str
    llm_mode: LLMMode
    hardware_mode: str
    providers: List[Dict[str, Any]] = Field(default_factory=list)
    cerebras_model: str = ""


class ConfirmRequest(BaseModel):
    confirmed: bool = True
    note: str = ""


class AgentVisionRequest(BaseModel):
    instruction: str
    scene_state: Dict[str, Any] = Field(default_factory=dict)
    image_path: Optional[str] = None


class AgentDecomposeRequest(BaseModel):
    instruction: str
    vision: Dict[str, Any]


class AgentSafetyRequest(BaseModel):
    subtask: Dict[str, Any]
    vision: Dict[str, Any]
    scene_state: Dict[str, Any]


class AgentPlanRequest(BaseModel):
    subtask: Dict[str, Any]
    safety: Dict[str, Any]
    localizer: Dict[str, Any]


class AgentReflectRequest(BaseModel):
    subtask: Dict[str, Any]
    actor_result: Dict[str, Any]
    scene_state: Dict[str, Any]
    image_path: Optional[str] = None