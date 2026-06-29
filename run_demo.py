"""Dependency-light CLI demo for VialPilot Swarm."""
from __future__ import annotations

import json

from src.vialpilot.agents.orchestrator_agent import run_swarm

if __name__ == "__main__":
    result = run_swarm(
        "Move the red sample vial to the safe tray, place the blue vial in the cold tray, avoid contamination, and verify the final arrangement.",
        "hazard_avoidance_scene",
    )
    print(json.dumps({
        "metrics": result["metrics"],
        "notebook": result["notebook"],
        "timeline_agents": [item["agent"] for item in result["timeline"]],
    }, indent=2))
