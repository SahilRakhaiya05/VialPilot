# VialPilot

**VialPilot** is an autonomous robotics lab with AI vision, nine specialist agents, and a 3D robot simulator.

Upload bench images, describe tasks in natural language, and watch agents observe → plan → act → verify in a closed loop.

---

## Features

- **Web dashboard** — create runs, vision input, live progress
- **3D robot simulator** — WebGL lab with sweep pick/place
- **9 agents** — Vision, Decompose, Localize, Safety, Plan, Act, Reflect, Notebook
- **Cerebras / Gemini** — live AI with offline mock when no API key
- **SQLite persistence** — history, reports, pipeline analyzer

---

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Add CEREBRAS_API_KEY to .env
python app.py
```

| URL | Description |
|---|---|
| http://localhost:7860 | Home |
| http://localhost:7860/dashboard | Dashboard |
| http://localhost:7860/simulator | 3D Robot Lab |
| http://localhost:7860/runs | History |
| http://localhost:8050 | Pipeline Analyzer |

---

## Robot simulator

| `SIMULATOR_MODE` | Behavior |
|---|---|
| `auto` (default) | Software 3D robot engine |
| `robot` | Same as auto |
| `lab_bench` | 2D bench only (fastest, used in tests) |

### Install simulator extras

```powershell
.\scripts\install_simulator.ps1
```

### Docker

```bash
docker compose -f docker-compose.simulator.yml up --build
```

---

## Environment

| Variable | Default | Description |
|---|---|---|
| `CEREBRAS_API_KEY` | — | Cerebras API key |
| `CEREBRAS_MODEL` | `auto` | Model id or auto-discover |
| `GEMINI_API_KEY` | — | Gemini fallback |
| `SIMULATOR_MODE` | `auto` | `auto`, `robot`, or `lab_bench` |
| `ROBOT_TASK_NAME` | `visual_manipulation` | Robot task id |
| `PORT` | `7860` | Web server port |

---

## Tests

```powershell
pytest
```

---

## Architecture

```text
upload → VisionLabAgent → TaskDecomposer → Localizer
  → [Safety → Plan → Actor → Reflect] → LabNotebook → report
                              ↓
                    3D Robot Simulator
```

---

## Project layout

```text
app.py
src/vialpilot/
  api/           # FastAPI + UI
  agents/        # 9 specialist agents
  simulator/     # Software robot + 2D bench
  llm/           # Cerebras + Gemini
  hardware/      # MQTT / webhook / sim
tests/
```