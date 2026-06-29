"""Closed-loop multi-agent workflow execution with live step commits."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.vialpilot.agents.actor_command_agent import actor_command_agent
from src.vialpilot.agents.lab_notebook_agent import lab_notebook_agent
from src.vialpilot.agents.localizer_agent import localizer_agent
from src.vialpilot.agents.motion_planner_agent import motion_planner_agent
from src.vialpilot.agents.reflector_agent import reflector_agent
from src.vialpilot.agents.safety_veto_agent import safety_veto_agent
from src.vialpilot.agents.task_decomposer_agent import task_decomposer_agent
from src.vialpilot.agents.vision_lab_agent import vision_lab_agent
from src.vialpilot.db import repository as repo
from src.vialpilot.db.models import RunRecord
from src.vialpilot.llm.client import get_active_model, get_active_provider
from src.vialpilot.models.schemas import AgentOutput
from src.vialpilot.services.files import image_mime_for_path, read_image_bytes
from src.vialpilot.services.reports import build_report
from src.vialpilot.simulator.factory import create_simulator, get_vision_input
from src.vialpilot.simulator.lab_bench import LabBench
from src.vialpilot.simulator.session import SimulatorSession

logger = logging.getLogger(__name__)


def _serialize_output(output: AgentOutput) -> Dict[str, Any]:
    return output.model_dump()


def _commit(db: Session, commit_each_step: bool) -> None:
    if commit_each_step:
        db.commit()


def _start_agent(db: Session, run: RunRecord, agent_name: str, commit_each_step: bool) -> None:
    repo.update_run(db, run, current_agent=agent_name)
    repo.add_event(db, run.id, "agent_started", agent_name=agent_name, message=f"{agent_name} started")
    _commit(db, commit_each_step)


def _persist_agent(db: Session, run_id: str, output: AgentOutput, commit_each_step: bool) -> None:
    repo.save_agent_output(db, run_id, output)
    repo.add_event(
        db,
        run_id,
        "agent_completed",
        agent_name=output.agent_name,
        message=output.summary,
        payload=_serialize_output(output),
    )
    _commit(db, commit_each_step)


def _robot_bench_snapshot(bench: LabBench, robot: Optional[SimulatorSession]) -> Dict[str, Any]:
    """Current bench layout including robot arm state when simulator is active."""
    if robot and hasattr(robot, "get_scene_state"):
        state = robot.get_scene_state()
        snap = dict(state.get("scene") or bench.state)
        snap["arm"] = state.get("arm", {})
        snap["robot"] = robot.status()
        return snap
    return dict(bench.state)


def _pick_image_bytes(run: RunRecord) -> Tuple[Optional[bytes], str]:
    frames = run.frame_paths or []
    if frames:
        path = frames[0]
        return read_image_bytes(path), image_mime_for_path(path)
    for path in run.upload_paths or []:
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            return read_image_bytes(path), image_mime_for_path(path)
    return None, "image/png"


def execute_run(db: Session, run: RunRecord, *, commit_each_step: bool = False) -> RunRecord:
    agent_outputs: List[Dict[str, Any]] = list(run.agent_outputs or [])
    safety_decisions: List[Dict[str, Any]] = list(run.safety_decisions or [])
    commands: List[Dict[str, Any]] = list(run.commands or [])
    latencies: Dict[str, float] = dict((run.latency_metrics or {}).get("per_agent_latency_ms", {}))
    human_confirmed = bool((run.run_meta or {}).get("human_confirmed"))

    try:
        repo.update_run(db, run, status="running", error_message=None, current_agent="Orchestrator")
        repo.add_event(db, run.id, "workflow_started", message="Agent workflow execution started")
        _commit(db, commit_each_step)

        simulator_mode, simulator = create_simulator(run.scene_id)
        bench = simulator if isinstance(simulator, LabBench) else LabBench.from_scene(run.scene_id)
        robot = simulator if isinstance(simulator, SimulatorSession) else None
        upload_image, upload_mime = _pick_image_bytes(run)
        image_bytes, scene_state = get_vision_input(simulator, run.scene_id, upload_image)
        image_mime = "image/png" if (robot and not upload_image) else (upload_mime if upload_image else "image/png")

        repo.update_run(db, run, run_meta={
            **(run.run_meta or {}),
            "simulator_mode": simulator_mode,
            "robot_backend": robot.status() if robot else None,
        })
        _commit(db, commit_each_step)

        _start_agent(db, run, "VisionLabAgent", commit_each_step)
        vision_out = vision_lab_agent.run(run.instruction, scene_state, image_bytes, image_mime)
        if vision_out.status == "failed":
            repo.update_run(
                db, run, status="failed",
                error_message=vision_out.summary,
                current_agent=None,
                agent_outputs=list(agent_outputs) + [_serialize_output(vision_out)],
            )
            repo.add_event(db, run.id, "workflow_failed", message=vision_out.summary)
            _commit(db, commit_each_step)
            return run
        _persist_agent(db, run.id, vision_out, commit_each_step)
        agent_outputs.append(_serialize_output(vision_out))
        latencies["VisionLabAgent"] = vision_out.latency_ms
        vision_data = vision_out.data
        repo.update_run(db, run, visual_observations=vision_data, agent_outputs=list(agent_outputs))
        _commit(db, commit_each_step)

        if not vision_data.get("objects"):
            repo.update_run(
                db, run, status="failed",
                error_message="No objects detected in visual analysis.",
                current_agent=None,
                latency_metrics=_metrics(agent_outputs, latencies),
            )
            repo.add_event(db, run.id, "workflow_failed", message="No objects detected")
            _commit(db, commit_each_step)
            return run

        _start_agent(db, run, "TaskDecomposerAgent", commit_each_step)
        decompose_out = task_decomposer_agent.run(run.instruction, vision_data)
        _persist_agent(db, run.id, decompose_out, commit_each_step)
        agent_outputs.append(_serialize_output(decompose_out))
        latencies["TaskDecomposerAgent"] = decompose_out.latency_ms

        _start_agent(db, run, "LocalizerAgent", commit_each_step)
        localizer_out = localizer_agent.run(vision_data)
        _persist_agent(db, run.id, localizer_out, commit_each_step)
        agent_outputs.append(_serialize_output(localizer_out))
        latencies["LocalizerAgent"] = localizer_out.latency_ms

        subtasks = decompose_out.data.get("subtasks", [])[:6]
        all_blocked = True
        needs_human = False

        for subtask in subtasks:
            _start_agent(db, run, "SafetyVetoAgent", commit_each_step)
            safety_out = safety_veto_agent.run(subtask, vision_data, bench.state, force_allow=human_confirmed)
            _persist_agent(db, run.id, safety_out, commit_each_step)
            agent_outputs.append(_serialize_output(safety_out))
            latencies[f"SafetyVetoAgent_{subtask.get('id', '')}"] = safety_out.latency_ms
            safety_decisions.append(safety_out.data)
            repo.update_run(db, run, agent_outputs=list(agent_outputs), safety_decisions=list(safety_decisions))
            _commit(db, commit_each_step)

            if safety_out.status == "blocked":
                needs_human = True
                if not human_confirmed:
                    continue
            else:
                all_blocked = False

            _start_agent(db, run, "MotionPlannerAgent", commit_each_step)
            planner_out = motion_planner_agent.run(subtask, safety_out.data, localizer_out.data)
            _persist_agent(db, run.id, planner_out, commit_each_step)
            agent_outputs.append(_serialize_output(planner_out))
            latencies[f"MotionPlannerAgent_{subtask.get('id', '')}"] = planner_out.latency_ms
            commands.append(planner_out.data)

            _start_agent(db, run, "ActorCommandAgent", commit_each_step)
            actor_out = actor_command_agent.run(
                bench, planner_out.data, robot=robot, simulator_mode=simulator_mode,
            )
            _persist_agent(db, run.id, actor_out, commit_each_step)
            agent_outputs.append(_serialize_output(actor_out))
            commands.append(actor_out.data)
            bench_snap = _robot_bench_snapshot(bench, robot)
            repo.update_run(db, run, bench_state=bench_snap, commands=list(commands))
            _commit(db, commit_each_step)

            _start_agent(db, run, "ReflectorAgent", commit_each_step)
            reflect_scene = bench_snap if robot else bench.state
            reflect_out = reflector_agent.run(subtask, actor_out.data, reflect_scene)
            _persist_agent(db, run.id, reflect_out, commit_each_step)
            agent_outputs.append(_serialize_output(reflect_out))

        _start_agent(db, run, "LabNotebookAgent", commit_each_step)
        notebook_out = lab_notebook_agent.run(
            run.instruction, bench.state.get("name", run.scene_id), agent_outputs, bench.serialize(),
        )
        _persist_agent(db, run.id, notebook_out, commit_each_step)
        agent_outputs.append(_serialize_output(notebook_out))

        if needs_human and not human_confirmed:
            final_status = "blocked"
            repo.add_event(db, run.id, "human_confirmation_required",
                           message="Safety blocked action — human confirmation required")
        elif all_blocked and subtasks:
            final_status = "blocked"
            repo.add_event(db, run.id, "workflow_blocked", message="Safety veto blocked all actions")
        else:
            final_status = "completed"

        run.visual_observations = vision_data
        run.agent_outputs = list(agent_outputs)
        run.safety_decisions = list(safety_decisions)
        run.commands = list(commands)
        run.bench_state = _robot_bench_snapshot(bench, robot)
        run.latency_metrics = _metrics(agent_outputs, latencies)
        run.final_report = build_report(run)
        repo.update_run(db, run, status=final_status, current_agent=None)
        repo.add_event(db, run.id, "workflow_completed", message=f"Run finished: {final_status}")
        _commit(db, commit_each_step)
        return run

    except Exception as exc:
        logger.exception("Workflow failed for run %s", run.id)
        repo.update_run(
            db, run, status="failed", error_message=str(exc), current_agent=None,
            agent_outputs=list(agent_outputs), safety_decisions=list(safety_decisions),
            commands=list(commands), latency_metrics=_metrics(agent_outputs, latencies),
        )
        repo.add_event(db, run.id, "workflow_failed", message=str(exc))
        _commit(db, commit_each_step)
        return run


def _metrics(agent_outputs: List[Dict[str, Any]], latencies: Dict[str, float]) -> Dict[str, Any]:
    total = sum(o.get("latency_ms", 0) for o in agent_outputs)
    real_calls = sum(1 for o in agent_outputs if o.get("mode") == "real")
    provider = get_active_provider()
    return {
        "agent_calls": len(agent_outputs),
        "total_latency_ms": round(total, 2),
        "per_agent_latency_ms": latencies,
        "real_llm_calls": real_calls,
        "llm_provider": provider,
        "model": get_active_model() if provider != "mock" else "mock-local",
    }