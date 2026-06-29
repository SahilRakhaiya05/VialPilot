"""Render lab-bench state as HTML for the dashboard."""
from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Optional


def render_bench_html(bench_state: Optional[Dict[str, Any]]) -> str:
    if not bench_state:
        return '<p class="hint">No bench state yet.</p>'
    state = bench_state.get("state", bench_state)
    width = int(state.get("bench_size", {}).get("width", 10))
    height = int(state.get("bench_size", {}).get("height", 6))
    zones = state.get("zones", [])
    objects = state.get("objects", [])

    def zone_at(x: int, y: int) -> Optional[Dict[str, Any]]:
        for zone in zones:
            if zone.get("x", 0) <= x < zone.get("x", 0) + zone.get("w", 0) and zone.get("y", 0) <= y < zone.get("y", 0) + zone.get("h", 0):
                return zone
        return None

    def objects_at(x: int, y: int) -> List[Dict[str, Any]]:
        return [o for o in objects if int(o.get("x", -1)) == x and int(o.get("y", -1)) == y]

    cells = []
    for y in range(height):
        for x in range(width):
            z = zone_at(x, y)
            cls = "bench-cell"
            label = ""
            if z:
                cls += " zone-" + z.get("kind", "zone")
                if x == z.get("x") and y == z.get("y"):
                    label = escape(z.get("label", ""))
            vials = ""
            for obj in objects_at(x, y):
                color = escape(obj.get("color", "gray"))
                title = escape(obj.get("label", obj.get("id", "")))
                oid = escape(obj.get("id", "?"))
                initial = oid[0].upper() if oid else "?"
                vials += f'<div class="vial vial-{color}" title="{title}">{initial}</div>'
            cells.append(f'<div class="{cls}"><small>{label}</small>{vials}</div>')

    return (
        f'<div class="bench-grid" style="grid-template-columns:repeat({width},1fr)">'
        f'{"".join(cells)}</div>'
    )


AGENT_STEPS = [
    ("VisionLabAgent", "Vision Lab", "eye"),
    ("TaskDecomposerAgent", "Decompose", "list"),
    ("LocalizerAgent", "Localize", "pin"),
    ("SafetyVetoAgent", "Safety", "shield"),
    ("MotionPlannerAgent", "Plan", "route"),
    ("ActorCommandAgent", "Execute", "play"),
    ("ReflectorAgent", "Verify", "check"),
    ("LabNotebookAgent", "Notebook", "book"),
]