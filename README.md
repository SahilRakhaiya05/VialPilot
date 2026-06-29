# VialPilot Swarm

**Autonomous robotics lab powered by Gemma 4 on Cerebras**

VialPilot turns multimodal AI into a real-time lab-bench controller. Upload a bench image or MP4 video, describe a task in natural language, and watch nine specialist agents **observe → reason → act → verify → replan** in a closed loop — with a live 3D robot arm in the browser.

Built for the **Cerebras × Google DeepMind Gemma 4 Hackathon** — *Multiverse Agents* track.

---

## Why VialPilot

| Hackathon pillar | What VialPilot does |
|------------------|---------------------|
| **Agent collaboration** | 9 coordinated agents with Reflector-triggered **one-shot replan** |
| **Multimodal intelligence** | Text + image + **MP4 video** (up to 4 frames) + **post-action simulator vision** |
| **Speed in action** | Per-agent latency, run-page **Speed in Action** panel, live **⚡ Speed Benchmark** |
| **Physical AI innovation** | Closed embodied loop driving a **WebGL 3D robot lab** — not a chatbot |

---

## Features

- **Dashboard** — natural-language instructions, image/video upload, simulator camera capture
- **9 specialist agents** — Vision, Decompose, Localize, Safety, Plan, Act, Reflect, Notebook (+ Orchestrator)
- **3D robot simulator** — WebGL arm with sweep pick/place, hazard zones, live command sync
- **Replan loop** — Reflector verifies each move; on failure, Motion Planner retries with a hint
- **Speed demo** — `POST /api/benchmark/speed` + UI buttons on Dashboard & Settings
- **Cerebras + Gemini** — live Gemma 4 31B on Cerebras; offline mock when no API key
- **SQLite persistence** — run history, audit reports, event timeline

---

## Quick start

### 1. Clone & install

```powershell
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure API key

Edit `.env` and add your Cerebras key:

```env
CEREBRAS_API_KEY=your_key_here
```

> Without a key, the app runs in **offline mock mode** (fine for tests, not for live demo).

### 3. Run

```bash
python app.py
```

| URL | Page |
|-----|------|
| http://127.0.0.1:7860 | Home |
| http://127.0.0.1:7860/dashboard | **Start workflows here** |
| http://127.0.0.1:7860/simulator | 3D Robot Lab |
| http://127.0.0.1:7860/runs | Run history |
| http://127.0.0.1:7860/settings | AI config & speed benchmark |
| http://127.0.0.1:8050 | Pipeline Analyzer (optional) |

---

## 60-second demo

1. Open **Dashboard** → select a scene (e.g. Hazard Avoidance)
2. Upload a **PNG/JPG** or **MP4 video** (or click **Simulator Capture**)
3. Enter: *"Move the red sample vial to the safe tray and avoid the contaminated zone."*
4. Click **▶ Start Workflow** → watch the agent stepper and **Speed in Action** panel
5. Open **Simulator** → see the arm sweep pick/place
6. Click **⚡ Speed Benchmark** → show live Gemma 4 latency on Cerebras

---

## Agent pipeline

```
User instruction + vision (image / video / simulator frame)
        │
        ▼
  VisionLabAgent ──► TaskDecomposerAgent ──► LocalizerAgent
        │
        ▼
  ┌─ SafetyVetoAgent ──► MotionPlannerAgent ──► ActorCommandAgent
  │                              ▲                      │
  │                              │ replan hint          ▼
  └─ ReflectorAgent ◄──── post-action vision frame   3D Simulator
        │
        ▼
  LabNotebookAgent ──► final report & audit trail
```

| Agent | Role |
|-------|------|
| Orchestrator | Runs the full workflow |
| Vision Lab | Multimodal scene analysis (multi-frame video) |
| Task Decomposer | Natural language → subtasks |
| Localizer | Object coordinates on the bench |
| Safety Veto | Blocks hazardous moves |
| Motion Planner | Robot motion commands |
| Actor Command | Executes commands in simulator |
| Reflector | Post-action visual verification + **replan trigger** |
| Lab Notebook | Audit trail and final summary |

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CEREBRAS_API_KEY` | — | **Required for live demo** — Cerebras API key |
| `CEREBRAS_MODEL` | `auto` | Model id or `auto` (discovers Gemma 4 31B) |
| `CEREBRAS_BASE_URL` | `https://api.cerebras.ai/v1` | Cerebras API base URL |
| `GEMINI_API_KEY` | — | Gemini fallback provider |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model id |
| `APP_MODE` | `development` | `development` enables hot reload |
| `PORT` | `7860` | Web server port |
| `SIMULATOR_MODE` | `auto` | `auto`, `robot`, or `lab_bench` |
| `MAX_VIDEO_FRAMES` | `8` | Frames extracted from uploaded MP4 |
| `MAX_VISION_FRAMES` | `4` | Frames sent to Gemma 4 vision per call |
| `ENABLE_PIPELINE_ANALYZER` | `true` | Set `false` to skip Dash analyzer |
| `DASH_PORT` | `8050` | Pipeline Analyzer port |
| `HARDWARE_MODE` | `simulation` | `simulation`, `mqtt`, or `webhook` |
| `MQTT_BROKER_URL` | — | Optional real-hardware MQTT bridge |
| `WEBHOOK_COMMAND_URL` | — | Optional webhook command endpoint |

See [`.env.example`](.env.example) for the full list.

---

## API highlights

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Server & LLM status |
| `/api/runs` | POST | Create a new lab run |
| `/api/runs/{id}/upload` | POST | Upload image and/or MP4 video |
| `/api/runs/{id}/execute` | POST | Start the agent workflow |
| `/api/benchmark/speed` | POST | Gemma 4 vision latency benchmark |
| `/api/settings` | GET | Active provider and model info |

---

## Tests

```bash
pytest
```

**24 tests** cover workflow, uploads, benchmark, safety, reports, and HTML routes.

---

## Docker

```bash
docker build -t vialpilot .
docker run -p 7860:7860 --env-file .env vialpilot
```

For the simulator stack with PyBullet (Linux):

```bash
docker compose -f docker-compose.simulator.yml up --build
```

---

## Project structure

```
app.py                      # Entry point
requirements.txt            # Single install file
SUBMISSION.md               # Hackathon submission brief
src/vialpilot/
  api/                      # FastAPI routes + Jinja UI
  agents/                   # 9 specialist agents
  llm/                      # Cerebras Gemma 4 + Gemini clients
  services/                 # Workflow, benchmark, reports, uploads
  simulator/                # 3D software robot + 2D bench
  static/                   # app.js, lab3d.js, simulator.js, CSS
  templates/                # Dashboard, simulator, run detail pages
tests/                      # Pytest suite
```

---

## Tech stack

- **Python 3.9+** · **FastAPI** · **SQLite** · **Jinja2**
- **Cerebras** OpenAI-compatible API · **Gemma 4 31B**
- **Google Gemini** fallback
- **Three.js** 3D robotics lab (browser)
- **OpenCV** video frame extraction

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 7860 busy | Kill old `python app.py` processes or set `PORT=7861` |
| Stale UI after updates | Hard refresh: **Ctrl+Shift+R** |
| Benchmark returns 404 | Restart server after pulling latest code |
| `Offline` badge in nav | Add `CEREBRAS_API_KEY` to `.env` and restart |
| OpenCV missing for video | `pip install opencv-python-headless` |

---

## Attribution

VialPilot Swarm is an original autonomous lab implementation for the **Cerebras × Google DeepMind Gemma 4 Hackathon**. Inspired by multi-agent robotics frameworks; built as a closed-loop embodied agent demo.

See [`SUBMISSION.md`](SUBMISSION.md) for the official hackathon write-up.