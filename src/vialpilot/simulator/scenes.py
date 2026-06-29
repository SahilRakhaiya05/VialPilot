"""Built-in demo scenes for VialPilot."""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, Any

SCENES: Dict[str, Dict[str, Any]] = {
    "safe_sorting_scene": {
        "name": "Safe Sorting Scene",
        "description": "Sort all red, blue, and green blocks into the correct trays without exceeding safety zones.",
        "bench_size": {"width": 10, "height": 6},
        "objects": [
            {"id": "red_vial", "label": "red sample vial", "color": "red", "zone": "input_rack", "x": 2, "y": 2, "state": "unmoved", "confidence": 0.96},
            {"id": "blue_vial", "label": "blue cold-chain vial", "color": "blue", "zone": "input_rack", "x": 2, "y": 3, "state": "unmoved", "confidence": 0.94},
            {"id": "green_vial", "label": "green waste vial", "color": "green", "zone": "input_rack", "x": 2, "y": 4, "state": "unmoved", "confidence": 0.93},
        ],
        "zones": [
            {"id": "input_rack", "label": "Input Rack", "kind": "source", "x": 0, "y": 0, "w": 3, "h": 6},
            {"id": "safe_tray", "label": "Safe Tray", "kind": "destination", "x": 7, "y": 0, "w": 3, "h": 2},
            {"id": "cold_tray", "label": "Cold Tray", "kind": "destination", "x": 7, "y": 2, "w": 3, "h": 2},
            {"id": "waste_tray", "label": "Waste Tray", "kind": "destination", "x": 7, "y": 4, "w": 3, "h": 2},
        ],
        "hazards": [],
    },
    "hazard_avoidance_scene": {
        "name": "Hazard Avoidance Scene",
        "description": "A contaminated zone blocks the direct path to the destination.",
        "bench_size": {"width": 10, "height": 6},
        "objects": [
            {"id": "red_vial", "label": "red sample vial", "color": "red", "zone": "input_rack", "x": 1, "y": 2, "state": "unmoved", "confidence": 0.95},
            {"id": "blue_vial", "label": "blue cold-chain vial", "color": "blue", "zone": "input_rack", "x": 1, "y": 4, "state": "unmoved", "confidence": 0.91},
        ],
        "zones": [
            {"id": "input_rack", "label": "Input Rack", "kind": "source", "x": 0, "y": 0, "w": 3, "h": 6},
            {"id": "safe_tray", "label": "Safe Tray", "kind": "destination", "x": 7, "y": 0, "w": 3, "h": 3},
            {"id": "cold_tray", "label": "Cold Tray", "kind": "destination", "x": 7, "y": 3, "w": 3, "h": 3},
            {"id": "contaminated_zone", "label": "Contaminated Zone", "kind": "hazard", "x": 4, "y": 1, "w": 2, "h": 4},
        ],
        "hazards": [
            {"id": "contaminated_zone", "risk": "critical", "reason": "No object path may cross this region."}
        ],
    },
    "uncertainty_scene": {
        "name": "Uncertainty Scene",
        "description": "A blurry label forces the Safety Agent to ask for human confirmation.",
        "bench_size": {"width": 10, "height": 6},
        "objects": [
            {"id": "unclear_vial", "label": "possibly red vial / label blurry", "color": "orange", "zone": "input_rack", "x": 1, "y": 2, "state": "uncertain", "confidence": 0.48},
        ],
        "zones": [
            {"id": "input_rack", "label": "Input Rack", "kind": "source", "x": 0, "y": 0, "w": 3, "h": 6},
            {"id": "safe_tray", "label": "Safe Tray", "kind": "destination", "x": 7, "y": 0, "w": 3, "h": 3},
            {"id": "waste_tray", "label": "Waste Tray", "kind": "destination", "x": 7, "y": 3, "w": 3, "h": 3},
        ],
        "hazards": [],
    },
}


def get_scene(scene_id: str) -> Dict[str, Any]:
    return deepcopy(SCENES.get(scene_id, SCENES["safe_sorting_scene"]))
