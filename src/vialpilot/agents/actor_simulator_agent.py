from __future__ import annotations

from typing import Dict, Any

from src.vialpilot.simulator.lab_bench import LabBench


def run(bench: LabBench, command: Dict[str, Any]) -> Dict[str, Any]:
    return bench.apply_command(command)
