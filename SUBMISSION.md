# VialPilot Swarm — Hackathon Submission

## Project Name
VialPilot Swarm

## Track
Multiverse Agents — Best Multi-Agent + Multimodal Use Case

## One-liner
VialPilot Swarm turns Gemma 4 31B on Cerebras into a real-time autonomous lab-bench swarm that sees sample vials, plans safe robot actions, executes them in a simulator, and visually verifies success.

## Description
VialPilot Swarm demonstrates how ultra-fast multimodal inference changes physical AI. Instead of producing a static report, the system stays inside a closed action loop. A user gives a lab-bench task and an image or frame of the bench. Specialist agents inspect the scene, decompose the task, localize objects, enforce safety constraints, generate robot-style commands, update a physical simulator, and verify the outcome. If the evidence is uncertain, the swarm asks for human confirmation instead of hallucinating a risky action.

## Agent Collaboration
The demo coordinates nine specialist agents:

- Orchestrator Agent
- Vision Lab Agent
- Task Decomposer Agent
- Localizer Agent
- Safety Veto Agent
- Motion Planner Agent
- Actor / Simulator Agent
- Reflector Agent
- Lab Notebook Agent

The Safety Veto Agent can block or change commands before the Actor executes them. The Reflector Agent checks the result and can force replanning.

## Multimodal Intelligence
The system combines:

- natural-language lab instruction
- uploaded image or frame
- simulated visual state
- structured coordinates and zone metadata
- JSON command logs
- final audit notebook

## Speed in Action
Each agent call logs latency and provider. When `CEREBRAS_API_KEY` is configured, model-backed agents use Gemma 4 31B through Cerebras' OpenAI-compatible endpoint. The UI shows per-agent latency and full-loop timing so judges can see why fast inference matters for observe → reason → act → verify loops.

## Innovation
VialPilot Swarm is an autonomous lab-bench controller, not a chatbot or report dashboard. It connects multimodal reasoning to physical-world commands such as moving a vial, avoiding a contaminated zone, requesting human confirmation, and verifying final placement.

## Demo Flow
1. Select the Hazard Avoidance Scene.
2. Enter: “Move the red sample vial to the safe tray and avoid the contaminated zone.”
3. Run the swarm.
4. Show the agent timeline, safety decision, simulator command, final lab-bench state, and latency panel.

## Tech Stack
- Python
- Flask
- Cerebras OpenAI-compatible API
- Gemma 4 31B
- Deterministic lab-bench simulator
- JSON-first agent outputs

## Attribution
This project is inspired by / derived from the MALLVI multi-agent robotics framework. Original attribution should be preserved when publishing the fork.
