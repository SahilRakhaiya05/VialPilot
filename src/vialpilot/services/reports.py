"""Report generation in JSON and Markdown."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.vialpilot.db.models import RunRecord
from src.vialpilot.llm.client import get_active_provider


def build_report(run: RunRecord) -> Dict[str, Any]:
    agent_outputs = run.agent_outputs or []
    vision = run.visual_observations or {}
    return {
        "run_id": run.id,
        "instruction": run.instruction,
        "scene_id": run.scene_id,
        "status": run.status,
        "timestamp": (run.updated_at or datetime.now(timezone.utc)).isoformat(),
        "llm_provider": get_active_provider(),
        "visual_observations": vision,
        "detected_objects": vision.get("objects", []),
        "subtasks": _extract_subtasks(agent_outputs),
        "safety_decisions": run.safety_decisions or [],
        "commands": run.commands or [],
        "final_state": run.bench_state,
        "unresolved_uncertainties": vision.get("uncertainties", []),
        "latency_metrics": run.latency_metrics or {},
        "agent_outputs": agent_outputs,
        "upload_paths": run.upload_paths or [],
        "frame_paths": run.frame_paths or [],
        "error_message": run.error_message,
    }


def _extract_subtasks(agent_outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for output in agent_outputs:
        if output.get("agent_name") == "TaskDecomposerAgent":
            return output.get("data", {}).get("subtasks", [])
    return []


def report_to_json(run: RunRecord, pretty: bool = True) -> str:
    data = build_report(run)
    if pretty:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    return json.dumps(data, ensure_ascii=False, default=str)


def report_to_markdown(run: RunRecord) -> str:
    report = build_report(run)
    lines = [
        f"# VialPilot Run Report",
        "",
        f"**Run ID:** `{report['run_id']}`",
        f"**Status:** {report['status']}",
        f"**Timestamp:** {report['timestamp']}",
        f"**LLM Provider:** {report['llm_provider']}",
        "",
        "## Instruction",
        report["instruction"],
        "",
        "## Visual Summary",
        vision_summary(report.get("visual_observations", {})),
        "",
        "## Detected Objects",
        _md_list_objects(report.get("detected_objects", [])),
        "",
        "## Subtasks",
        _md_list_subtasks(report.get("subtasks", [])),
        "",
        "## Safety Decisions",
        _md_list_dicts(report.get("safety_decisions", [])),
        "",
        "## Commands",
        _md_list_dicts(report.get("commands", [])),
        "",
        "## Latency Metrics",
        "```json",
        json.dumps(report.get("latency_metrics", {}), indent=2),
        "```",
        "",
        "## Unresolved Uncertainties",
        _md_list_dicts(report.get("unresolved_uncertainties", [])),
        "",
    ]
    if report.get("error_message"):
        lines.extend(["## Error", report["error_message"], ""])
    return "\n".join(lines)


def vision_summary(vision: Dict[str, Any]) -> str:
    return vision.get("visual_summary", "No visual summary available.")


def _md_list_objects(objects: List[Dict[str, Any]]) -> str:
    if not objects:
        return "_No objects detected._"
    return "\n".join(
        f"- **{o.get('id', '?')}** ({o.get('label', '')}) — confidence {o.get('confidence', 'n/a')}"
        for o in objects
    )


def _md_list_subtasks(subtasks: List[Dict[str, Any]]) -> str:
    if not subtasks:
        return "_No subtasks generated._"
    return "\n".join(
        f"- **{s.get('id', '?')}**: {s.get('goal', '')} → `{s.get('destination', '')}`"
        for s in subtasks
    )


def _md_list_dicts(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "_None._"
    return "\n".join(f"- `{json.dumps(item, ensure_ascii=False)}`" for item in items)