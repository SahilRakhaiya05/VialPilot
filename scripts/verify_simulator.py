"""Verify VialPilot robot simulator works after install."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.vialpilot.simulator.session import get_session

s = get_session(force_new=True)
s.reset()
png = s.get_frame_png()
st = s.status()
print(f"OK: {s.mode} backend, frame={len(png)} bytes")
print(f"Backend: {st.get('backend', '?')}")
print(f"PyBullet: {st.get('pybullet', False)}")