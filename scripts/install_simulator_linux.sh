#!/usr/bin/env bash
# VialPilot robot simulator install (Linux/Docker)
set -euo pipefail
cd "$(dirname "$0")/.."

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel

pip install -r requirements.txt
pip install -r requirements-robot-lite.txt
pip install -r requirements-robot-full.txt || true

python scripts/verify_simulator.py
echo "Start: python app.py"