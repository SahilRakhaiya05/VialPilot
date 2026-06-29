"""Render robot-lab camera frames — perspective lab bench with UR5-style arm."""
from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

COLORS = {
    "red": (220, 55, 55),
    "blue": (45, 115, 220),
    "green": (45, 175, 85),
    "orange": (230, 135, 35),
    "gray": (130, 138, 150),
}

ZONE_COLORS = {
    "source": (42, 52, 78),
    "destination": (32, 62, 52),
    "hazard": (78, 28, 28),
}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _zone_fill(zone: Dict[str, Any]) -> Tuple[int, int, int]:
    kind = zone.get("kind", "destination")
    return ZONE_COLORS.get(kind, ZONE_COLORS["destination"])


def _draw_vial(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: Tuple[int, int, int], label: str) -> None:
    w, h = 22, 34
    x0, y0 = cx - w // 2, cy - h // 2
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=6, fill=color, outline=(240, 245, 255), width=2)
    draw.ellipse([x0 + 4, y0 - 6, x0 + w - 4, y0 + 4], fill=(200, 205, 215))
    draw.text((x0 - 4, y0 + h + 2), label[:14], fill=(210, 218, 230))


def _draw_arm(draw: ImageDraw.ImageDraw, base_x: int, base_y: int, reach: float, grip: bool, held: bool) -> None:
    """Simple 3-link UR5-style arm from base."""
    angle = _lerp(-0.4, 0.5, reach)
    l1, l2, l3 = 55, 45, 28
    j1x = base_x + int(math.cos(angle) * l1)
    j1y = base_y - int(math.sin(angle) * l1 * 0.6)
    j2x = j1x + int(math.cos(angle + 0.35) * l2)
    j2y = j1y - int(math.sin(angle + 0.35) * l2 * 0.5)
    tipx = j2x + int(math.cos(angle + 0.7) * l3)
    tipy = j2y - int(math.sin(angle + 0.7) * l3 * 0.4)

    for pts, w in [((base_x, base_y, j1x, j1y), 7), ((j1x, j1y, j2x, j2y), 6), ((j2x, j2y, tipx, tipy), 5)]:
        draw.line(pts, fill=(160, 175, 195), width=w)
    draw.ellipse([base_x - 10, base_y - 10, base_x + 10, base_y + 10], fill=(70, 78, 95))
    gw = 6 if grip else 14
    draw.rectangle([tipx - gw, tipy - 4, tipx + gw, tipy + 8], fill=(100, 110, 130))
    if held:
        draw.ellipse([tipx - 8, tipy + 6, tipx + 8, tipy + 22], fill=(220, 55, 55))


def render_frame(
    scene: Dict[str, Any],
    *,
    arm_pos: Tuple[float, float] = (0.5, 0.15),
    gripper_open: bool = True,
    holding_object_id: Optional[str] = None,
    size: Tuple[int, int] = (640, 360),
) -> bytes:
    """Perspective robot-lab camera view as PNG bytes."""
    w, h = size
    img = Image.new("RGB", (w, h), (8, 12, 22))
    draw = ImageDraw.Draw(img)

    # Floor gradient
    for y in range(h):
        t = y / h
        c = int(_lerp(18, 32, t))
        draw.line([(0, y), (w, y)], fill=(c, c + 4, c + 10))

    # Table (trapezoid perspective)
    tm, bm = 80, h - 30
    tl, tr, bl, br = 100, w - 100, 40, w - 40
    draw.polygon([(tl, tm), (tr, tm), (br, bm), (bl, bm)], fill=(38, 44, 58), outline=(70, 80, 100))

    bench = scene.get("bench_size", {"width": 10, "height": 6})
    bw, bh = bench.get("width", 10), bench.get("height", 6)

    def to_px(x: float, y: float) -> Tuple[int, int]:
        px = _lerp(tl, bl, y / bh) + (x / bw) * (_lerp(tr, br, y / bh) - _lerp(tl, bl, y / bh))
        py = _lerp(tm, bm, y / bh)
        return int(px), int(py)

    # Grid lines
    for i in range(int(bw) + 1):
        x = i
        p0 = to_px(x, 0)
        p1 = to_px(x, bh)
        draw.line([*p0, *p1], fill=(50, 58, 72))
    for j in range(int(bh) + 1):
        p0 = to_px(0, j)
        p1 = to_px(bw, j)
        draw.line([*p0, *p1], fill=(50, 58, 72))

    for zone in scene.get("zones", []):
        x0, y0 = to_px(zone["x"], zone["y"])
        x1, y1 = to_px(zone["x"] + zone["w"], zone["y"] + zone["h"])
        fill = _zone_fill(zone)
        draw.rectangle([x0, y0, x1, y1], fill=fill, outline=(90, 100, 120))
        draw.text((x0 + 6, y0 + 4), zone.get("label", zone["id"])[:16], fill=(200, 210, 225))

    held_id = holding_object_id if not gripper_open else None
    for obj in scene.get("objects", []):
        if held_id and obj["id"] == held_id:
            continue
        cx, cy = to_px(obj.get("x", 1), obj.get("y", 1))
        color = COLORS.get(obj.get("color", "gray"), COLORS["gray"])
        _draw_vial(draw, cx, cy, color, obj.get("label", obj.get("id", "")))

    arm_base_x = int(_lerp(bl + 30, br - 30, arm_pos[0]))
    arm_base_y = bm - 10
    _draw_arm(draw, arm_base_x, arm_base_y, arm_pos[0], gripper_open, held_id is not None)

    draw.text((12, 10), f"VialPilot — {scene.get('name', 'Bench')}", fill=(82, 104, 128))
    draw.text((12, h - 22), "AI vision · Robotics Lab", fill=(100, 115, 130))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def scene_for_vision(scene: Dict[str, Any]) -> Dict[str, Any]:
    objects: List[Dict[str, Any]] = []
    for obj in scene.get("objects", []):
        objects.append({
            "id": obj["id"],
            "label": obj.get("label", obj["id"]),
            "color": obj.get("color"),
            "zone": obj.get("zone"),
            "x": obj.get("x"),
            "y": obj.get("y"),
            "state": obj.get("state", "visible"),
            "confidence": obj.get("confidence", 0.9),
        })
    return {
        "name": scene.get("name"),
        "description": scene.get("description"),
        "objects": objects,
        "zones": scene.get("zones", []),
        "hazards": scene.get("hazards", []),
        "simulator": "vialpilot-robot",
    }