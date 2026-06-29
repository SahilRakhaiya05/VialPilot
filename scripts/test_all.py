#!/usr/bin/env python3
"""Quick integration test — API, simulator, Gemma 4."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from src.vialpilot.api.app import create_app
from src.vialpilot.llm.client import get_active_model, get_active_provider, run_json

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  OK  {name}")


def bad(name: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("=== VialPilot Integration Test ===\n")

    provider = get_active_provider()
    model = get_active_model()
    print(f"AI: {provider} / {model}")
    if provider == "cerebras-gemma4":
        ok("Gemma 4 Cerebras active")
    elif provider == "gemini":
        ok("Gemini active (add CEREBRAS_API_KEY for Gemma 4)")
    else:
        bad("No live AI provider")

    llm = run_json(
        agent_name="Test",
        system_prompt='Return JSON {"ping":true}',
        user_prompt="ping",
        fallback_json={"ping": False},
    )
    if llm.mode == "real" and llm.error is None:
        ok(f"Live LLM call ({llm.latency_ms}ms)")
    else:
        bad("Live LLM call", llm.error or "mock")

    client = TestClient(create_app())

    h = client.get("/api/health")
    if h.status_code == 200 and h.json().get("llm_mode") == "real":
        ok("/api/health")
    else:
        bad("/api/health", str(h.json()))

    for path, needle in [
        ("/", "Autonomous Lab"),
        ("/dashboard", "Autonomous Lab Dashboard"),
        ("/simulator", "Sweep Demo"),
        ("/runs", "Run History"),
        ("/settings", "Settings"),
    ]:
        r = client.get(path)
        if r.status_code == 200 and needle in r.text:
            ok(f"HTML {path}")
        else:
            bad(f"HTML {path}")

    init = client.post("/simulator/init", json={"scene_id": "safe_sorting_scene", "force_new": True})
    if init.status_code == 200:
        ok("/simulator/init")
    else:
        bad("/simulator/init")

    scene = client.get("/simulator/scene")
    data = scene.json()
    if scene.status_code == 200 and data.get("scene", {}).get("objects"):
        ok("/simulator/scene")
    else:
        bad("/simulator/scene")

    frame = client.get("/simulator/frame.png")
    if frame.status_code == 200 and frame.headers.get("content-type", "").startswith("image"):
        ok("/simulator/frame.png")
    else:
        bad("/simulator/frame.png")

    for cmd in [
        {"command": "PICK_OBJECT", "object_id": "red_vial"},
        {"command": "PLACE_OBJECT", "object_id": "red_vial", "to": "safe_tray"},
        {"command": "PICK_OBJECT", "object_id": "blue_vial"},
        {"command": "PLACE_OBJECT", "object_id": "blue_vial", "to": "cold_tray"},
    ]:
        step = client.post("/simulator/step", json=cmd)
        if step.status_code == 200 and step.json().get("applied"):
            ok(f"robot {cmd['command']} {cmd.get('object_id','')}")
        else:
            bad(f"robot {cmd['command']}", str(step.json()))

    create = client.post("/api/runs", json={
        "instruction": "Integration test — sort vials",
        "scene_id": "safe_sorting_scene",
    })
    if create.status_code != 200:
        bad("/api/runs create")
    else:
        ok("/api/runs create")
        run_id = create.json()["run_id"]
        detail_page = client.get(f"/runs/{run_id}")
        if detail_page.status_code == 200 and "run-shell" in detail_page.text:
            ok(f"/runs/{run_id} HTML")
        else:
            bad(f"/runs/{run_id} HTML")

    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())