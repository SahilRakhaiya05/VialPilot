"""VialPilot — unified entry (FastAPI dashboard + optional Pipeline Analyzer)."""
from __future__ import annotations

import os
import socket

import uvicorn

from src.vialpilot.config import DATA_DIR, UPLOAD_DIR


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def _pick_port(preferred: int) -> int:
    if _port_free(preferred):
        return preferred
    for alt in range(preferred + 1, preferred + 10):
        if _port_free(alt):
            print(f"Port {preferred} busy (old server?) — using {alt}")
            return alt
    return preferred


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if os.getenv("ENABLE_PIPELINE_ANALYZER", "true").lower() in ("1", "true", "yes"):
        dash_port = int(os.getenv("DASH_PORT", "8050"))
        try:
            from src.vialpilot.pipeline_analyzer import start_analyzer_thread

            start_analyzer_thread(port=dash_port)
            print(f"Pipeline Analyzer: http://127.0.0.1:{dash_port}")
        except Exception as exc:
            print(f"Pipeline Analyzer not started (pip install dash plotly pandas): {exc}")

    preferred = int(os.getenv("PORT", "7860"))
    port = _pick_port(preferred)
    print(f"VialPilot: http://127.0.0.1:{port}")
    print(f"  Dashboard:       http://127.0.0.1:{port}/dashboard")
    print(f"  Robot Simulator: http://127.0.0.1:{port}/simulator")
    uvicorn.run(
        "src.vialpilot.api.app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("APP_MODE", "development") == "development",
    )