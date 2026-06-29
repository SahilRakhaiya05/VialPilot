# VialPilot Swarm — Hackathon Submission

## Project Name
VialPilot Swarm

## Track
Multiverse Agents — Best Multi-Agent + Multimodal Use Case

## One-liner
VialPilot Swarm turns **Gemma 4 31B on Cerebras** into a real-time autonomous lab-bench swarm that sees sample vials (image + video frames), plans safe robot actions, executes them in a 3D simulator, visually verifies outcomes, and replans when needed.

## Description
VialPilot demonstrates how **ultra-fast multimodal inference** changes physical AI. Instead of a static report, the system runs a closed **observe → reason → act → verify → replan** loop. A user gives a lab instruction plus an image, video (MP4), or live simulator frame. Nine specialist agents inspect the scene, decompose tasks, localize objects, enforce safety, plan robot commands, execute in the 3D lab, **verify with post-action vision**, and audit results. If verification fails, the Reflector triggers a **one-shot replan** before continuing.

## Agent Collaboration
Nine coordinated agents:

| Agent | Role |
|-------|------|
| Orchestrator | Workflow execution |
| Vision Lab | Multimodal scene analysis (multi-frame video) |
| Task Decomposer | NL → subtasks |
| Localizer | Object coordinates |
| Safety Veto | Blocks hazardous moves |
| Motion Planner | Robot commands |
| Actor Command | Executes in simulator |
| Reflector | Post-action visual verification + **replan trigger** |
| Lab Notebook | Audit trail |

**Replan loop:** When Reflector sets `retry_needed`, Motion Planner re-runs with the reflector hint, Actor retries, Reflector verifies again.

## Multimodal Intelligence
- **Text:** Natural-language lab instructions
- **Images:** Upload PNG/JPG/WEBP or simulator camera capture
- **Video:** MP4 upload → up to 8 frames extracted → **up to 4 frames** sent to Gemma 4 vision in one call
- **Post-action vision:** Reflector receives fresh simulator frame after each move
- **Structured:** Zones, hazards, coordinates, JSON command logs

Requires `CEREBRAS_API_KEY` for live Gemma 4 31B (offline mock available for tests only).

## Speed in Action
- Per-agent `latency_ms` on every AI call
- Run page **Speed in Action** panel: wall clock, avg AI latency, live call count, replan count
- Dashboard **⚡ Speed Benchmark** — 3× Vision agent calls with avg/min/max ms
- Workflow `speed_summary` e.g. *"9 agents · 4.2s wall · 6 Gemma 4 calls avg 850ms on Cerebras"*

## Innovation (Physical AI)
Autonomous **lab-bench controller** with:
- 3D WebGL robot arm (sweep pick/place)
- Hazard zone avoidance
- Human-in-the-loop for uncertain labels
- MQTT/webhook bridge for real hardware
- Closed-loop embodied agent — not a chatbot

## Demo Flow (60 seconds)
1. **Dashboard** → Hazard Avoidance scene
2. Upload image **or MP4 video** (or Simulator Capture)
3. Instruction: *"Move the red sample vial to the safe tray and avoid the contaminated zone."*
4. **Start Workflow** → watch agent stepper + **Speed in Action** panel
5. Open **Simulator** tab → arm sweep animation
6. Click **⚡ Speed Benchmark** to show Cerebras latency live

## Tech Stack
- **Python 3.9+**
- **FastAPI** + SQLite
- **Cerebras** OpenAI-compatible API
- **Gemma 4 31B** (auto-discovered)
- Three.js 3D robotics lab
- Google Gemini fallback

## Setup
```bash
pip install -r requirements.txt
# Add to .env:
CEREBRAS_API_KEY=your_key
python app.py
# http://127.0.0.1:7860
```

## Attribution
Inspired by multi-agent robotics frameworks. VialPilot is an original autonomous lab implementation for the Cerebras × Google DeepMind Gemma 4 Hackathon.