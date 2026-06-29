"""Closed-loop multi-agent workflow execution with live step commits."""
from __future__ import annotations

import logging
import time
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
from src.vialpilot.config import MAX_VISION_FRAMES
from src.vialpilot.db import repository as repo
from src.vialpilot.db.models import RunRecord
from src.vialpilot.llm.client import get_active_model, get_active_provider
from src.vialpilot.llm.images import ImageFrame
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


def _pick_vision_frames(run: RunRecord) -> List[ImageFrame]:
    """Uploaded video frames (multi) or single image."""
    frames: List[ImageFrame] = []
    for path in run.frame_paths or []:
        try:
            frames.append((read_image_bytes(path), image_mime_for_path(path)))
        except Exception:
            continue
    if frames:
        return frames[:MAX_VISION_FRAMES]
    for path in run.upload_paths or []:
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            return [(read_image_bytes(path), image_mime_for_path(path))]
    return []


def _verification_frame(robot: Optional[SimulatorSession]) -> Tuple[Optional[bytes], str, List[ImageFrame]]:
    if robot and hasattr(robot, "get_frame_png"):
        try:
            png = robot.get_frame_png()
            return png, "image/png", [(png, "image/png")]
        except Exception:
            pass
    return None, "image/png", []


def _execute_subtask(
    db: Session,
    run: RunRecord,
    subtask: Dict[str, Any],
    vision_data: Dict[str, Any],
    safety_out: AgentOutput,
    localizer_out: AgentOutput,
    bench: LabBench,
    robot: Optional[SimulatorSession],
    simulator_mode: str,
    commit_each_step: bool,
    agent_outputs: List[Dict[str, Any]],
    latencies: Dict[str, float],
    commands: List[Dict[str, Any]],
    allow_replan: bool = True,
) -> Tuple[bool, bool]:
    """Plan → act → reflect (with optional replan). Returns (needs_human, replanned)."""
    sid = subtask.get("id", "")
    replanned = False

    def _plan_act_reflect(retry_hint: str = "", is_replan: bool = False) -> AgentOutput:
        nonlocal replanned
        tag = f"_{sid}_replan" if is_replan else f"_{sid}"
        agent_label = "MotionPlannerAgent" + (" (replan)" if is_replan else "")

        _start_agent(db, run, agent_label, commit_each_step)
        planner_out = motion_planner_agent.run(
            subtask, safety_out.data, localizer_out.data, retry_hint=retry_hint,
        )
        _persist_agent(db, run.id, planner_out, commit_each_step)
        agent_outputs.append(_serialize_output(planner_out))
        latencies[f"MotionPlannerAgent{tag}"] = planner_out.latency_ms
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

        post_bytes, post_mime, post_frames = _verification_frame(robot)
        _start_agent(db, run, "ReflectorAgent" + (" (replan)" if is_replan else ""), commit_each_step)
        reflect_out = reflector_agent.run(
            subtask,
            actor_out.data,
            bench_snap,
            image_bytes=post_bytes,
            image_mime=post_mime,
            frames=post_frames or None,
            is_replan=is_replan,
        )
        _persist_agent(db, run.id, reflect_out, commit_each_step)
        agent_outputs.append(_serialize_output(reflect_out))
        latencies[f"ReflectorAgent{tag}"] = reflect_out.latency_ms
        if is_replan:
            replanned = True
        return reflect_out

    reflect_out = _plan_act_reflect()
    if (
        allow_replan
        and reflect_out.data.get("retry_needed")
        and not reflect_out.data.get("success")
    ):
        hint = reflect_out.data.get("next_recommendation", "Retry with adjusted route.")
        repo.add_event(db, run.id, "replan_started", message=f"Reflector requested replan: {hint}")
        _commit(db, commit_each_step)
        reflect_out = _plan_act_reflect(retry_hint=hint, is_replan=True)
        repo.add_event(
            db, run.id, "replan_completed",
            message="Replan finished" if reflect_out.data.get("success") else "Replan still failing",
        )
        _commit(db, commit_each_step)

    return False, replanned


def execute_run(db: Session, run: RunRecord, *, commit_each_step: bool = False) -> RunRecord:
    agent_outputs: List[Dict[str, Any]] = list(run.agent_outputs or [])
    safety_decisions: List[Dict[str, Any]] = list(run.safety_decisions or [])
    commands: List[Dict[str, Any]] = list(run.commands or [])
    latencies: Dict[str, float] = dict((run.latency_metrics or {}).get("per_agent_latency_ms", {}))
    human_confirmed = bool((run.run_meta or {}).get("human_confirmed"))
    loop_started = time.perf_counter()

    try:
        repo.update_run(db, run, status="running", error_message=None, current_agent="Orchestrator")
        repo.add_event(db, run.id, "workflow_started", message="Agent workflow execution started")
        _commit(db, commit_each_step)

        simulator_mode, simulator = create_simulator(run.scene_id)
        bench = simulator if isinstance(simulator, LabBench) else LabBench.from_scene(run.scene_id)
        robot = simulator if isinstance(simulator, SimulatorSession) else None
        vision_frames = _pick_vision_frames(run)
        upload_image = vision_frames[0][0] if vision_frames else None
        image_bytes, scene_state = get_vision_input(simulator, run.scene_id, upload_image)
        image_mime = vision_frames[0][1] if vision_frames else "image/png"
        if not vision_frames and image_bytes:
            vision_frames = [(image_bytes, image_mime)]

        repo.update_run(db, run, run_meta={
            **(run.run_meta or {}),
            "simulator_mode": simulator_mode,
            "robot_backend": robot.status() if robot else None,
            "vision_frame_count": len(vision_frames),
        })
        _commit(db, commit_each_step)

        _start_agent(db, run, "VisionLabAgent", commit_each_step)
        vision_out = vision_lab_agent.run(
            run.instruction, scene_state,
            frames=vision_frames or None,
            image_bytes=image_bytes if not vision_frames else None,
            image_mime=image_mime,
        )
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
                latency_metrics=_metrics(agent_outputs, latencies, loop_started),
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
        replan_count = 0

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

            _, did_replan = _execute_subtask(
                db, run, subtask, vision_data, safety_out, localizer_out,
                bench, robot, simulator_mode, commit_each_step,
                agent_outputs, latencies, commands,
            )
            if did_replan:
                replan_count += 1

        final_snap = _robot_bench_snapshot(bench, robot)
        _start_agent(db, run, "LabNotebookAgent", commit_each_step)
        notebook_out = lab_notebook_agent.run(
            run.instruction,
            final_snap.get("name", run.scene_id),
            agent_outputs,
            final_snap,
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
        run.bench_state = final_snap
        metrics = _metrics(agent_outputs, latencies, loop_started, replan_count=replan_count)
        run.latency_metrics = metrics
        run.final_report = build_report(run)
        repo.update_run(db, run, status=final_status, current_agent=None)
        repo.add_event(
            db, run.id, "workflow_completed",
            message=f"Run finished: {final_status} — {metrics.get('speed_summary', '')}",
        )
        _commit(db, commit_each_step)
        return run

    except Exception as exc:
        logger.exception("Workflow failed for run %s", run.id)
        repo.update_run(
            db, run, status="failed", error_message=str(exc), current_agent=None,
            agent_outputs=list(agent_outputs), safety_decisions=list(safety_decisions),
            commands=list(commands), latency_metrics=_metrics(agent_outputs, latencies, loop_started),
        )
        repo.add_event(db, run.id, "workflow_failed", message=str(exc))
        _commit(db, commit_each_step)
        return run


def _metrics(
    agent_outputs: List[Dict[str, Any]],
    latencies: Dict[str, float],
    loop_started: Optional[float] = None,
    replan_count: int = 0,
) -> Dict[str, Any]:
    total = sum(o.get("latency_ms", 0) for o in agent_outputs)
    real_outputs = [o for o in agent_outputs if o.get("mode") == "real"]
    real_calls = len(real_outputs)
    real_latency = sum(o.get("latency_ms", 0) for o in real_outputs)
    provider = get_active_provider()
    model = get_active_model()
    wall_ms = round((time.perf_counter() - loop_started) * 1000, 2) if loop_started else total
    avg_llm = round(real_latency / real_calls, 2) if real_calls else 0.0

    if provider == "cerebras-gemma4":
        speed_summary = (
            f"{len(agent_outputs)} agents · {wall_ms / 1000:.1f}s wall · "
            f"{real_calls} Gemma 4 calls avg {avg_llm:.0f}ms on Cerebras"
        )
    elif not real_calls:
        speed_summary = f"{len(agent_outputs)} agents · configure CEREBRAS_API_KEY for Gemma 4"
    else:
        speed_summary = f"{len(agent_outputs)} agents · {wall_ms / 1000:.1f}s wall"

    return {
        "agent_calls": len(agent_outputs),
        "total_latency_ms": round(total, 2),
        "wall_clock_ms": wall_ms,
        "per_agent_latency_ms": latencies,
        "real_llm_calls": real_calls,
        "avg_llm_latency_ms": avg_llm,
        "replan_count": replan_count,
        "llm_provider": provider,
        "model": model,
        "speed_summary": speed_summary,
        "cerebras_advantage": provider == "cerebras-gemma4",
    }