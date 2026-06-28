"""Application configuration from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
if os.getenv("VIALPILOT_SKIP_LOCAL_ENV") != "1":
    load_dotenv(ROOT_DIR / ".env.local", override=True)
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(DATA_DIR / "uploads")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'vialpilot.db'}")

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "").strip()
CEREBRAS_BASE_URL = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
# Cerebras Gemma 4 — use "auto" to discover from API, or explicit id e.g. gemma-4-31b
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "auto")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

APP_MODE = os.getenv("APP_MODE", "development")
ENABLE_PIPELINE_ANALYZER = os.getenv("ENABLE_PIPELINE_ANALYZER", "true").lower() in ("1", "true", "yes")
DASH_PORT = int(os.getenv("DASH_PORT", "8050"))

# Simulator: auto | robot | lab_bench (all use VialPilot software robotics engine)
SIMULATOR_MODE = os.getenv("SIMULATOR_MODE", "auto")
ROBOT_TASK_NAME = os.getenv("ROBOT_TASK_NAME", "visual_manipulation")
ROBOT_OBS_DIR = Path(os.getenv("ROBOT_OBS_DIR", str(DATA_DIR / "robot_observations")))
ROBOT_DISPLAY_GUI = os.getenv("ROBOT_DISPLAY_GUI", "false").lower() in ("1", "true", "yes")

HARDWARE_MODE = os.getenv("HARDWARE_MODE", "simulation")
MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "").strip()
WEBHOOK_COMMAND_URL = os.getenv("WEBHOOK_COMMAND_URL", "").strip()

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_VIDEO_EXT = {".mp4"}
MAX_VIDEO_FRAMES = int(os.getenv("MAX_VIDEO_FRAMES", "8"))