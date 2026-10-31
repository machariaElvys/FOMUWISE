import json
import logging
import os
import time

from app.errors import ApiError


class GemmaService:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_config(cls, config):
        api_key = config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ApiError(
                "AI_NOT_CONFIGURED",
                "The backend is missing its GEMINI_API_KEY configuration.",
                503,
            )
        return cls(api_key, config.get("GEMMA_MODEL", "gemma-4-26b-a4b-it"))

    def _call(self, prompt):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            started_at = time.perf_counter()
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                    max_output_tokens=3072,
                ),
            )
            logging.getLogger(__name__).info(
                "Gemma request finished in %.2fs (prompt=%d chars, response=%d chars)",
                time.perf_counter() - started_at,
                len(prompt),
                len(response.text or ""),
            )
            text = (response.text or "").strip()
            fence = chr(96) * 3
            if text.startswith(fence):
                text = text.split("\n", 1)[-1]
                if text.endswith(fence):
                    text = text[:-3]
            return text.strip()
        except Exception as error:
            if getattr(error, "status_code", None) == 429:
                raise ApiError(
                    "AI_RATE_LIMITED",
                    "The AI service is temporarily rate-limited. Please wait and try again.",
                    429,
                )
            raise ApiError(
                "AI_UNAVAILABLE",
                "The AI service could not process this request. Please try again.",
                503,
            )

    def generate_json(self, prompt):
        response_text = self._call(prompt)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            repair_prompt = (
                "Convert the following response into valid JSON only. Preserve its data. "
                "Do not add facts. Return no markdown.\n\n" + response_text[:12000]
            )
            try:
                return json.loads(self._call(repair_prompt))
            except (json.JSONDecodeError, ApiError):
                raise ApiError(
                    "AI_OUTPUT_INVALID",
                    "The AI service returned an unusable response. Please retry.",
                    502,
                )
