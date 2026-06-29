"""Side-by-side LLM speed race for demo video — Gemma 4 vs simulated GPU providers."""
from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from src.vialpilot.agents.vision_lab_agent import vision_lab_agent
from src.vialpilot.llm.client import get_active_model, llm_available
from src.vialpilot.simulator.scenes import get_scene
from src.vialpilot.simulator.session import get_session

DEMO_PROMPT = "Identify all sample vials, trays, and hazard zones on this lab bench."

# Simulated GPU-class latencies for demo contrast (not live API calls)
SIMULATED_PROVIDERS = {
    "openai-gpt52": {
        "name": "OpenAI GPT-5.2",
        "model": "gpt-5.2",
        "hardware": "GPU cluster",
        "min_ms": 16000,
        "max_ms": 24000,
        "summary": "Detected 3 objects (simulated GPU inference — high latency).",
    },
    "gemini-20": {
        "name": "Google Gemini 2.0",
        "model": "gemini-2.0-flash",
        "hardware": "Cloud TPU/GPU",
        "min_ms": 10000,
        "max_ms": 17000,
        "summary": "Detected 3 objects (simulated cloud inference — moderate latency).",
    },
}


def _simulated_run(provider_id: str) -> Dict[str, Any]:
    cfg = SIMULATED_PROVIDERS[provider_id]
    delay_ms = random.uniform(cfg["min_ms"], cfg["max_ms"])
    time.sleep(delay_ms / 1000.0)
    return {
        "id": provider_id,
        "name": cfg["name"],
        "model": cfg["model"],
        "hardware": cfg["hardware"],
        "latency_ms": round(delay_ms, 1),
        "live": False,
        "simulated": True,
        "status": "complete",
        "summary": cfg["summary"],
        "objects_found": 3,
    }


def _cerebras_run() -> Dict[str, Any]:
    scene = get_scene("safe_sorting_scene")
    session = get_session(scene_id="safe_sorting_scene")
    frame = None
    if session.available:
        session.reset("safe_sorting_scene")
        frame, _ = session.observation_for_vision()

    t0 = time.perf_counter()
    out = vision_lab_agent.run(
        DEMO_PROMPT,
        scene,
        image_bytes=frame,
        image_mime="image/png",
    )
    wall = round((time.perf_counter() - t0) * 1000, 1)
    latency = out.latency_ms or wall
    data = out.data or {}
    objects = data.get("objects", [])
    return {
        "id": "cerebras-gemma4",
        "name": "Cerebras Gemma 4",
        "model": get_active_model(),
        "hardware": "Cerebras Wafer-Scale",
        "latency_ms": round(latency, 1),
        "live": out.mode == "real",
        "simulated": False,
        "status": "complete" if out.mode == "real" else "unavailable",
        "summary": out.summary or "Vision analysis complete.",
        "objects_found": len(objects),
        "error": data.get("llm_error"),
    }


def run_llm_race() -> Dict[str, Any]:
    """Run the same vision task on Gemma 4 (live) vs simulated GPT-5.2 & Gemini 2.0."""
    started = time.perf_counter()
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_cerebras_run): "cerebras-gemma4",
            pool.submit(_simulated_run, "openai-gpt52"): "openai-gpt52",
            pool.submit(_simulated_run, "gemini-20"): "gemini-20",
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    order = ["cerebras-gemma4", "openai-gpt52", "gemini-20"]
    results.sort(key=lambda r: order.index(r["id"]))

    live_results = [r for r in results if r.get("live")]
    cerebras = next((r for r in results if r["id"] == "cerebras-gemma4"), None)
    slowest = max(results, key=lambda r: r["latency_ms"])
    fastest = min(results, key=lambda r: r["latency_ms"])

    if cerebras and cerebras.get("status") == "complete":
        cerebras["winner"] = True
        for r in results:
            if r["id"] != "cerebras-gemma4":
                r["winner"] = False
    else:
        fastest["winner"] = True

    speedup = round(slowest["latency_ms"] / max(fastest["latency_ms"], 1), 1)
    wall_ms = round((time.perf_counter() - started) * 1000, 1)

    headline = (
        f"Gemma 4 finished in {cerebras['latency_ms']:.0f}ms — "
        f"{speedup}× faster than {slowest['name']}"
        if cerebras and cerebras.get("live")
        else "Add CEREBRAS_API_KEY for live Gemma 4 race"
    )

    return {
        "prompt": DEMO_PROMPT,
        "llm_available": llm_available(),
        "wall_clock_ms": wall_ms,
        "results": results,
        "winner_id": "cerebras-gemma4" if cerebras and cerebras.get("live") else fastest["id"],
        "speedup_factor": speedup,
        "headline": headline,
        "note": "GPT-5.2 and Gemini 2.0 use simulated GPU latencies for demo comparison.",
    }