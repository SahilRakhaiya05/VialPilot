"""Helpers for multimodal image payloads."""
from __future__ import annotations

from typing import List, Optional, Tuple

ImageFrame = Tuple[bytes, str]


def normalize_frames(
    image_bytes: Optional[bytes] = None,
    image_mime: str = "image/png",
    frames: Optional[List[ImageFrame]] = None,
    max_frames: int = 4,
) -> List[ImageFrame]:
    out: List[ImageFrame] = []
    if frames:
        for data, mime in frames:
            if data:
                out.append((data, mime or "image/jpeg"))
    elif image_bytes:
        out.append((image_bytes, image_mime or "image/png"))
    return out[:max_frames]