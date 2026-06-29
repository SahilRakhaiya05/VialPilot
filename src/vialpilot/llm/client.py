"""Unified LLM client: Cerebras Gemma 4 (primary) → Gemini. No mock when keys exist."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.vialpilot.llm.cerebras_gemma import CerebrasGemmaClient
from src.vialpilot.llm.images import ImageFrame
from src.vialpilot.llm.gemini_client import GeminiClient
from src.vialpilot.models.schemas import LLMResult

logger = logging.getLogger(__name__)

_cerebras: Optional[CerebrasGemmaClient] = None
_gemini: Optional[GeminiClient] = None


def _cerebras_client() -> CerebrasGemmaClient:
    global _cerebras
    if _cerebras is None:
        _cerebras = CerebrasGemmaClient()
    return _cerebras


def _gemini_client() -> GeminiClient:
    global _gemini
    if _gemini is None:
        _gemini = GeminiClient()
    return _gemini


def llm_available() -> bool:
    return _cerebras_client().enabled or _gemini_client().enabled


def get_active_model() -> str:
    if _cerebras_client().enabled:
        return _cerebras_client().model
    if _gemini_client().enabled:
        return _gemini_client().model
    return "mock-local"


def get_active_provider() -> str:
    if _cerebras_client().enabled:
        return "cerebras-gemma4"
    if _gemini_client().enabled:
        return "gemini"
    return "mock"


def get_provider_status() -> List[Dict[str, Any]]:
    from src.vialpilot.llm.cerebras_models import GEMMA4_DEFAULT_MODEL

    cerebras = _cerebras_client()
    gemini = _gemini_client()
    has_real = cerebras.enabled or gemini.enabled
    return [
        {
            "id": "cerebras-gemma4",
            "name": "Cerebras Gemma 4",
            "model": cerebras.model if cerebras.enabled else GEMMA4_DEFAULT_MODEL,
            "enabled": cerebras.enabled,
            "priority": 1,
        },
        {
            "id": "gemini",
            "name": "Google Gemini",
            "model": gemini.model,
            "enabled": gemini.enabled,
            "priority": 2,
        },
        {
            "id": "mock",
            "name": "Offline (tests only)",
            "model": "mock-local",
            "enabled": not has_real,
            "priority": 3,
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
    gemini = _gemini_client()

    gemma_system = (
        f"You are {agent_name or 'a VialPilot lab agent'} powered by Gemma 4 on Cerebras.\n"
        + system_prompt
        + "\nRespond with a single valid JSON object only. No markdown fences."
    )

    errors: List[str] = []

    if cerebras.enabled:
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
        errors.append(f"Cerebras: {result.error}")

    if gemini.enabled:
        result = gemini.run_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            fallback_json=fallback_json,
            image_bytes=image_bytes,
            image_mime=image_mime,
            images=images,
            temperature=temperature,
        )
        if result.mode == "real":
            return result
        errors.append(f"Gemini: {result.error}")
        return LLMResult(
            mode="mock",
            model=gemini.model,
            latency_ms=0.0,
            raw_text="",
            result_json={},
            error=" | ".join(errors),
        )

    # Tests / offline only — deterministic fallback
    return LLMResult(
        mode="mock",
        model="mock-local",
        latency_ms=30.0,
        raw_text=str(fallback_json),
        result_json=fallback_json,
        error=None if not llm_available() else " | ".join(errors),
    )