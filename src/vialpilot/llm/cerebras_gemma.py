"""Cerebras Gemma 4 — multimodal vision + JSON agent calls."""
from __future__ import annotations

import base64
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from src.vialpilot.config import CEREBRAS_API_KEY, CEREBRAS_BASE_URL, CEREBRAS_MODEL
from src.vialpilot.llm.cerebras_models import GEMMA4_DEFAULT_MODEL, resolve_gemma4_model
from src.vialpilot.llm.images import ImageFrame, normalize_frames
from src.vialpilot.models.schemas import LLMResult
from src.vialpilot.utils.json_parse import extract_json

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


class CerebrasGemmaClient:
    def __init__(self) -> None:
        self.api_key = CEREBRAS_API_KEY
        self.base_url = CEREBRAS_BASE_URL
        self.configured_model = CEREBRAS_MODEL or GEMMA4_DEFAULT_MODEL
        self.enabled = bool(self.api_key) and OpenAI is not None
        self._client: Optional[OpenAI] = None
        self.model = GEMMA4_DEFAULT_MODEL
        if self.enabled:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.model = resolve_gemma4_model(self._client, self.configured_model)

    def refresh_model(self) -> str:
        """Re-resolve Gemma 4 model from Cerebras API."""
        if self._client:
            self.model = resolve_gemma4_model(self._client, self.configured_model)
        return self.model

    def run_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        fallback_json: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png",
        images: Optional[List[ImageFrame]] = None,
        temperature: float = 1.0,
    ) -> LLMResult:
        if not self.enabled or self._client is None:
            return LLMResult(
                mode="unavailable",
                model=self.model,
                latency_ms=0.0,
                raw_text="",
                result_json={},
                error="CEREBRAS_API_KEY not configured",
            )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt + "\nReturn strict JSON only."},
        ]
        frame_list = normalize_frames(image_bytes, image_mime, images)
        if frame_list:
            content: List[Dict[str, Any]] = [{"type": "text", "text": user_prompt}]
            for data, mime in frame_list:
                if mime not in ("image/png", "image/jpeg", "image/jpg"):
                    mime = "image/png"
                data_url = f"data:{mime};base64,{base64.b64encode(data).decode('utf-8')}"
                content.append({"type": "image_url", "image_url": {"url": data_url}})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": user_prompt})

        last_error: Optional[str] = None
        for attempt in range(2):
            start = time.perf_counter()
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                text = response.choices[0].message.content or "{}"
                return LLMResult(
                    mode="real",
                    model=self.model,
                    latency_ms=latency_ms,
                    raw_text=text,
                    result_json=extract_json(text, fallback_json),
                    error=None,
                )
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Cerebras Gemma 4 attempt %d failed (%s): %s", attempt + 1, self.model, exc)
                if "response_format" in last_error.lower() or "json_object" in last_error.lower():
                    try:
                        response = self._client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=temperature,
                        )
                        latency_ms = round((time.perf_counter() - start) * 1000, 2)
                        text = response.choices[0].message.content or "{}"
                        return LLMResult(
                            mode="real",
                            model=self.model,
                            latency_ms=latency_ms,
                            raw_text=text,
                            result_json=extract_json(text, fallback_json),
                            error=None,
                        )
                    except Exception as exc2:
                        last_error = str(exc2)
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                break

        return LLMResult(
            mode="unavailable",
            model=self.model,
            latency_ms=0.0,
            raw_text="",
            result_json={},
            error=last_error or "Cerebras Gemma 4 API unavailable",
        )


cerebras_client = CerebrasGemmaClient()