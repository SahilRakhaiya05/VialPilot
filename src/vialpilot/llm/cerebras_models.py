"""Discover Gemma 4 model IDs from the Cerebras Inference API."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from openai import OpenAI

logger = logging.getLogger(__name__)

# Official Cerebras catalog: https://inference-docs.cerebras.ai/models/gemma-4-31b
GEMMA4_DEFAULT_MODEL = "gemma-4-31b"
GEMMA4_MODEL_CANDIDATES = (
    "gemma-4-31b",
    "gemma-4-31B-it",
    "google/gemma-4-31b-it",
    "gemma-4",
)


def _is_gemma4(model_id: str) -> bool:
    mid = model_id.lower()
    return "gemma-4" in mid or "gemma4" in mid


def pick_gemma4_model(model_ids: List[str], configured: str = "") -> str:
    """Pick the best Gemma 4 model from a list returned by the API."""
    if configured and configured.lower() not in ("auto", ""):
        if configured in model_ids:
            return configured
        logger.warning("Configured CEREBRAS_MODEL=%s not in API list; using anyway", configured)
        return configured

    for candidate in GEMMA4_MODEL_CANDIDATES:
        if candidate in model_ids:
            return candidate

    for mid in model_ids:
        if _is_gemma4(mid):
            return mid

    return GEMMA4_DEFAULT_MODEL


def list_models_from_client(client: "OpenAI") -> List[str]:
    """List model IDs from authenticated Cerebras /v1/models."""
    try:
        response = client.models.list()
        return [m.id for m in response.data if getattr(m, "id", None)]
    except Exception as exc:
        logger.warning("Cerebras models.list failed: %s", exc)
        return []


def resolve_gemma4_model(client: Optional["OpenAI"], configured: str = "") -> str:
    """Resolve Gemma 4 model ID — API discovery with documented fallback."""
    if client is not None:
        ids = list_models_from_client(client)
        if ids:
            chosen = pick_gemma4_model(ids, configured)
            logger.info("Cerebras Gemma 4 model: %s (from %d API models)", chosen, len(ids))
            return chosen
    if configured and configured.lower() not in ("auto", ""):
        return configured
    return GEMMA4_DEFAULT_MODEL


def fetch_public_model_info(model_id: str = GEMMA4_DEFAULT_MODEL) -> Optional[Dict[str, Any]]:
    """Best-effort public catalog lookup (no API key)."""
    url = f"https://api.cerebras.ai/public/v1/models/{model_id}"
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            return response.json()
    except Exception as exc:
        logger.debug("Public model catalog unavailable: %s", exc)
    return {
        "id": model_id,
        "name": "Gemma 4 31B",
        "capabilities": {"vision": True, "structured_outputs": True},
        "preview": True,
    }