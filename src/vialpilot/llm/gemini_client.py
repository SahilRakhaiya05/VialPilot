"""Google Gemini client for multimodal lab-bench analysis."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from src.vialpilot.config import GEMINI_API_KEY, GEMINI_MODEL
from src.vialpilot.models.schemas import LLMResult
from src.vialpilot.llm.images import ImageFrame, normalize_frames
from src.vialpilot.utils.json_parse import extract_json

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore


class GeminiClient:
    def __init__(self) -> None:
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.enabled = bool(self.api_key) and genai is not None
        self._client = None
        if self.enabled:
            self._client = genai.Client(api_key=self.api_key)

    def run_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        fallback_json: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png",
        images: Optional[List[ImageFrame]] = None,
        temperature: float = 0.1,
    ) -> LLMResult:
        if not self.enabled or self._client is None:
            return LLMResult(
                mode="mock",
                model=self.model,
                latency_ms=30.0,
                raw_text=str(fallback_json),
                result_json=fallback_json,
                error=None,
            )

        contents: list = [user_prompt]
        if types is not None:
            for data, mime in normalize_frames(image_bytes, image_mime, images):
                contents.append(types.Part.from_bytes(data=data, mime_type=mime))

        last_error: Optional[str] = None
        for attempt in range(2):
            start = time.perf_counter()
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt + "\nReturn strict JSON only.",
                        temperature=temperature,
                    ),
                )
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                text = response.text or "{}"
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
                logger.warning("Gemini API attempt %d failed: %s", attempt + 1, exc)
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                break

        return LLMResult(
            mode="mock",
            model=self.model,
            latency_ms=0.0,
            raw_text="",
            result_json=fallback_json,
            error=last_error or "Gemini API unavailable",
        )


gemini_client = GeminiClient()