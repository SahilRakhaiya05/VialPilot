"""File upload and video frame extraction."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import UploadFile

from src.vialpilot.config import (
    ALLOWED_IMAGE_EXT,
    ALLOWED_IMAGE_TYPES,
    ALLOWED_VIDEO_EXT,
    MAX_VIDEO_FRAMES,
    UPLOAD_DIR,
)

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


class FileServiceError(Exception):
    pass


def ensure_upload_dir(run_id: str) -> Path:
    path = UPLOAD_DIR / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_upload(filename: str, content_type: Optional[str]) -> str:
    ext = _ext(filename)
    if ext in ALLOWED_IMAGE_EXT:
        if content_type and content_type not in ALLOWED_IMAGE_TYPES and content_type != "application/octet-stream":
            raise FileServiceError(f"Invalid image content type: {content_type}")
        return "image"
    if ext in ALLOWED_VIDEO_EXT:
        return "video"
    raise FileServiceError(f"Unsupported file type: {ext}. Allowed: png, jpg, jpeg, webp, mp4")


async def save_upload(run_id: str, upload: UploadFile) -> Tuple[str, str]:
    if not upload.filename:
        raise FileServiceError("Upload filename is required")
    kind = validate_upload(upload.filename, upload.content_type)
    dest_dir = ensure_upload_dir(run_id)
    dest = dest_dir / Path(upload.filename).name
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return str(dest), kind


def extract_video_frames(video_path: str, run_id: str, max_frames: int = MAX_VIDEO_FRAMES) -> List[str]:
    if cv2 is None:
        raise FileServiceError("OpenCV not installed; cannot extract video frames")

    path = Path(video_path)
    if not path.exists():
        raise FileServiceError(f"Video not found: {video_path}")

    frames_dir = ensure_upload_dir(run_id) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileServiceError("Could not open video file")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, total // max_frames) if total > 0 else 1
    saved: List[str] = []
    index = 0
    frame_idx = 0

    while len(saved) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if index % step == 0:
            out = frames_dir / f"frame_{frame_idx:04d}.jpg"
            cv2.imwrite(str(out), frame)
            saved.append(str(out))
            frame_idx += 1
        index += 1

    cap.release()
    if not saved:
        raise FileServiceError("No frames could be extracted from video")
    return saved


def read_image_bytes(path: str) -> bytes:
    p = Path(path)
    if not p.exists():
        raise FileServiceError(f"Image not found: {path}")
    return p.read_bytes()


def image_mime_for_path(path: str) -> str:
    ext = _ext(path)
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")