"""Convert VialPilot run events to pipeline log format."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _ts(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or datetime.now(timezone.utc).isoformat())


def run_to_log_lines(
    *,
    run_id: str,
    instruction: str,
    events: List[Dict[str, Any]],
    agent_outputs: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """Produce newline-delimited JSON logs compatible with LogProcessor."""
    lines: List[str] = []
    t0 = _ts(events[0].get("created_at") if events else None)

    lines.append(json.dumps({
        "timestamp": t0,
        "message": "Graph execution started",
        "data": {"run_id": run_id, "instruction": instruction, "source": "VialPilot"},
    }))

    agent_map = {
        "VisionLabAgent": "vision_lab",
        "TaskDecomposerAgent": "decomposer",
        "LocalizerAgent": "localizer",
        "SafetyVetoAgent": "safety_veto",
        "MotionPlannerAgent": "motion_planner",
        "ActorCommandAgent": "actor",
        "ReflectorAgent": "reflector",
        "LabNotebookAgent": "lab_notebook",
        "Orchestrator": "orchestrator",
    }

    for event in events:
        ts = _ts(event.get("created_at"))
        etype = event.get("event_type", "")
        agent = event.get("agent_name") or ""
        node = agent_map.get(agent, agent.lower() if agent else "system")
        payload = event.get("payload") or {}

        if etype == "workflow_started":
            lines.append(json.dumps({
                "timestamp": ts,
                "message": "Node started: orchestrator",
                "data": {"event": etype, "instruction": instruction},
            }))
        elif etype == "agent_started":
            lines.append(json.dumps({
                "timestamp": ts,
                "message": f"Node started: {node}",
                "data": {"agent": agent, "event": etype},
            }))
        elif etype == "agent_completed":
            lines.append(json.dumps({
                "timestamp": ts,
                "message": f"Node completed: {node}",
                "data": payload,
            }))
        elif etype in ("workflow_completed", "workflow_failed", "workflow_blocked"):
            lines.append(json.dumps({
                "timestamp": ts,
                "message": f"Task Complete: {etype}",
                "data": {"message": event.get("message", ""), "event": etype},
            }))
        elif etype == "human_confirmation_required":
            lines.append(json.dumps({
                "timestamp": ts,
                "message": "Verification: human confirmation required",
                "data": payload,
            }))
        else:
            lines.append(json.dumps({
                "timestamp": ts,
                "message": event.get("message", etype),
                "data": payload,
            }))

    if agent_outputs:
        for output in agent_outputs:
            node = agent_map.get(output.get("agent_name", ""), output.get("agent_name", "agent"))
            lines.append(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"Node completed: {node}",
                "data": {"result": output},
            }))

    end_ts = _ts(events[-1].get("created_at") if events else None)
    lines.append(json.dumps({
        "timestamp": end_ts,
        "message": "Graph execution completed",
        "data": {"run_id": run_id},
    }))
    return lines


def run_to_log_text(**kwargs) -> str:
    return "\n".join(run_to_log_lines(**kwargs))