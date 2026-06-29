"""Unified LLM client — Cerebras Gemma 4 only."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.vialpilot.llm.cerebras_gemma import CerebrasGemmaClient
from src.vialpilot.llm.images import ImageFrame
from src.vialpilot.models.schemas import LLMResult

logger = logging.getLogger(__name__)

_cerebras: Optional[CerebrasGemmaClient] = None


def _cerebras_client() -> CerebrasGemmaClient:
    global _cerebras
    if _cerebras is None:
        _cerebras = CerebrasGemmaClient()
    return _cerebras


def llm_available() -> bool:
    return _cerebras_client().enabled


def get_active_model() -> str:
    cerebras = _cerebras_client()
    return cerebras.model if cerebras.enabled else cerebras.model


def get_active_provider() -> str:
    return "cerebras-gemma4"


def get_provider_status() -> List[Dict[str, Any]]:
    from src.vialpilot.llm.cerebras_models import GEMMA4_DEFAULT_MODEL

    cerebras = _cerebras_client()
    return [
        {
            "id": "cerebras-gemma4",
            "name": "Cerebras Gemma 4",
            "model": cerebras.model if cerebras.enabled else GEMMA4_DEFAULT_MODEL,
            "enabled": cerebras.enabled,
            "priority": 1,
        },
    ]


def run_json(
    *,
    agent_name: str = "",
    system_prompt: str,
    user_prompt: str,
    fallback_json: Dict[str, Any],
    image_bytes: Optional[bytes] = None,
    image_mime: str = "image/png",
    images: Optional[List[ImageFrame]] = None,
    temperature: float = 0.1,
) -> LLMResult:
    cerebras = _cerebras_client()

    gemma_system = (
        f"You are {agent_name or 'a VialPilot lab agent'} powered by Gemma 4 on Cerebras.\n"
        + system_prompt
        + "\nRespond with a single valid JSON object only. No markdown fences."
    )

    if not cerebras.enabled:
        return LLMResult(
            mode="unavailable",
            model=cerebras.model,
            latency_ms=0.0,
            raw_text="",
            result_json={},
            error="CEREBRAS_API_KEY not configured — add to .env and restart",
        )

    result = cerebras.run_json(
        system_prompt=gemma_system,
        user_prompt=user_prompt,
        fallback_json=fallback_json,
        image_bytes=image_bytes,
        image_mime=image_mime,
        images=images,
        temperature=temperature,
    )
    if result.mode == "real":
        return result

    return LLMResult(
        mode="unavailable",
        model=cerebras.model,
        latency_ms=result.latency_ms,
        raw_text=result.raw_text,
        result_json={},
        error=result.error or "Cerebras Gemma 4 API call failed",
    )