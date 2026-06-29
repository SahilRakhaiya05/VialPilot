"""Robust JSON helpers for model outputs."""
from __future__ import annotations

import json
import re
from typing import Any, Dict


def extract_json(text: str, fallback: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return the first JSON object found in text, or fallback.

    Model responses sometimes include markdown fences or explanation text. This
    parser keeps the demo from crashing during judging.
    """
    fallback = fallback or {}
    if not text:
        return fallback

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {"value": value}
    except Exception:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {"value": value}
        except Exception:
            return fallback

    return fallback
