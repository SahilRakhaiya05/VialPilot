"""Cerebras / Gemma 4 speed benchmark for live demos."""
from __future__ import annotations

import statistics
import time
from typing import Any, Dict, List

from src.vialpilot.agents.vision_lab_agent import vision_lab_agent
from src.vialpilot.llm.client import get_active_model, get_active_provider, llm_available
from src.vialpilot.simulator.scenes import get_scene
from src.vialpilot.simulator.session import get_session


def run_speed_benchmark(iterations: int = 3) -> Dict[str, Any]:
    """Run repeated Vision agent calls to showcase inference latency."""
    provider = get_active_provider()
    model = get_active_model()
    scene = get_scene("safe_sorting_scene")
    session = get_session(scene_id="safe_sorting_scene")
    frame = None
    if session.available:
        session.reset("safe_sorting_scene")
        frame, _ = session.observation_for_vision()

    instruction = "Identify all sample vials and trays on the lab bench."
    samples: List[float] = []
    modes: List[str] = []

    for i in range(max(1, min(iterations, 5))):
        t0 = time.perf_counter()
        out = vision_lab_agent.run(
            instruction,
            scene,
            image_bytes=frame,
            image_mime="image/png",
        )
        wall = round((time.perf_counter() - t0) * 1000, 2)
        samples.append(out.latency_ms or wall)
        modes.append(out.mode)

    real = sum(1 for m in modes if m == "real")
    avg = round(statistics.mean(samples), 2) if samples else 0.0
    mn = round(min(samples), 2) if samples else 0.0
    mx = round(max(samples), 2) if samples else 0.0

    return {
        "provider": provider,
        "model": model,
        "llm_available": llm_available(),
        "iterations": len(samples),
        "latencies_ms": samples,
        "avg_ms": avg,
        "min_ms": mn,
        "max_ms": mx,
        "real_calls": real,
        "headline": (
            f"Gemma 4 on Cerebras: {avg:.0f}ms avg vision call ({mn:.0f}–{mx:.0f}ms)"
            if provider == "cerebras-gemma4" and real
            else (
                f"Vision benchmark: {avg:.0f}ms avg ({provider})"
                if real
                else "Configure CEREBRAS_API_KEY for live Gemma 4 speed demo"
            )
        ),
    }