from __future__ import annotations

from typing import Any, Dict, List

from src.vialpilot.agents.base import from_llm
from src.vialpilot.llm.client import run_json
from src.vialpilot.models.schemas import AgentOutput

SYSTEM = """You are the Task Decomposer Agent. Break lab instructions into atomic subtasks.
Return JSON: {"subtasks":[{"id":"T1","goal":"","target_object":"","destination":"","preconditions":[],"success_criteria":[]}]}"""


def _infer_destination(obj: Dict[str, Any], instruction: str) -> str:
    obj_text = (obj.get("label", "") + " " + obj.get("color", "") + " " + obj.get("id", "")).lower()
    if "blue" in obj_text or "cold" in obj_text:
        return "cold_tray"
    if "green" in obj_text or "waste" in obj_text:
        return "waste_tray"
    if "red" in obj_text or "safe" in instruction.lower():
        return "safe_tray"
    return "safe_tray"


def fallback_subtasks(instruction: str, vision: Dict[str, Any]) -> List[Dict[str, Any]]:
    subtasks: List[Dict[str, Any]] = []
    for index, obj in enumerate(vision.get("objects", []), start=1):
        if obj.get("confidence", 1.0) < 0.7:
            subtasks.append({
                "id": f"T{index}",
                "goal": f"Confirm identity of {obj.get('label', obj.get('id'))}",
                "target_object": obj.get("id"),
                "destination": "human_confirmation",
                "preconditions": ["Visual confidence below 0.70"],
                "success_criteria": ["Human confirms vial identity"],
            })
        else:
            destination = _infer_destination(obj, instruction)
            subtasks.append({
                "id": f"T{index}",
                "goal": f"Move {obj.get('label', obj.get('id'))} to {destination}",
                "target_object": obj.get("id"),
                "destination": destination,
                "preconditions": ["Object visible", "Safety veto passes"],
                "success_criteria": [f"{obj.get('id')} in {destination}"],
            })
    return subtasks


class TaskDecomposerAgent:
    name = "TaskDecomposerAgent"

    def run(self, instruction: str, vision: Dict[str, Any]) -> AgentOutput:
        fallback = {"subtasks": fallback_subtasks(instruction, vision)}
        prompt = f"Instruction: {instruction}\nVision: {vision}\nCreate ordered subtasks."
        llm = run_json(agent_name=self.name, system_prompt=SYSTEM, user_prompt=prompt, fallback_json=fallback)
        count = len(llm.json.get("subtasks", []))
        return from_llm(self.name, llm, summary=f"Decomposed into {count} subtask(s).", confidence=0.9)


task_decomposer_agent = TaskDecomposerAgent()