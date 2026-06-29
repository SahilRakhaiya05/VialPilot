from __future__ import annotations

from typing import Any, Dict, Optional

from src.vialpilot.agents.base import local_output
from src.vialpilot.hardware.bridge import bridge
from src.vialpilot.models.schemas import AgentOutput
from src.vialpilot.simulator.lab_bench import LabBench
from src.vialpilot.simulator.session import SimulatorSession


class ActorCommandAgent:
    name = "ActorCommandAgent"

    def run(
        self,
        bench: LabBench,
        command: Dict[str, Any],
        robot: Optional[SimulatorSession] = None,
        simulator_mode: str = "lab_bench",
    ) -> AgentOutput:
        result = bridge.dispatch(command, bench, robot=robot, simulator_mode=simulator_mode)
        applied = result.get("applied", False)
        return local_output(
            self.name,
            data=result,
            summary=result.get("message", "Command dispatched."),
            status="success" if applied else "warning",
            confidence=1.0 if applied else 0.5,
        )


actor_command_agent = ActorCommandAgent()