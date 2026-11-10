import json
import logging
import os
from importlib.metadata import PackageNotFoundError, version
from time import perf_counter

from app.errors import ApiError


logger = logging.getLogger(__name__)


def _http_status(value):
    candidates = (
        getattr(value, "status_code", None),
        getattr(value, "code", None),
        getattr(getattr(value, "response", None), "status_code", None),
    )
    for candidate in candidates:
        try:
            status = int(candidate)
        except (TypeError, ValueError):
            continue
        if 100 <= status <= 599:
            return status
    return None


def _usage_counts(response):
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return {}
    names = (
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
        "thoughts_token_count",
        "cached_content_token_count",
    )
    return {name: getattr(usage, name) for name in names if getattr(usage, name, None) is not None}


class GemmaService:
    def __init__(self, api_key, model, max_output_tokens=16384, timeout_ms=40000):
        self.api_key = api_key
        self.model = model
        self.max_output_tokens = int(max_output_tokens)
        self.timeout_ms = int(timeout_ms)
        if not 1000 <= self.timeout_ms <= 45000:
            raise ValueError("AI_TIMEOUT_MS must be between 1000 and 45000")
        self._client = None
        self._metrics = None
        try:
            self.sdk_version = version("google-genai")
        except PackageNotFoundError:
            self.sdk_version = None

    @classmethod
    def from_config(cls, config):
        api_key = config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ApiError(
                "AI_NOT_CONFIGURED",
                "The backend is missing its GEMINI_API_KEY configuration.",
                503,
            )
        return cls(
            api_key,
            config.get("GEMMA_MODEL", "gemma-4-26b-a4b-it"),
            config.get("MAX_OUTPUT_TOKENS", 16384),
            config.get("AI_TIMEOUT_MS", 40000),
        )

    def set_metrics(self, metrics):
        self._metrics = metrics
        if metrics is not None:
            metrics["model"] = self.model
            metrics["max_output_tokens"] = self.max_output_tokens
            metrics["thinking_level_configured"] = None
            metrics["genai_sdk_version"] = self.sdk_version
            metrics["sdk_retry_options_configured"] = True
            metrics["ai_timeout_ms"] = self.timeout_ms
            metrics["sdk_retry_count"] = 0

    def _client_for_request(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=self.timeout_ms,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        return self._client

    def _call(self, prompt):
        metrics = self._metrics
        input_characters = len(prompt)
        call_number = None
        if metrics is not None:
            metrics["ai_call_count"] = metrics.get("ai_call_count", 0) + 1
            metrics["gemini_input_characters"] = (
                metrics.get("gemini_input_characters", 0) + input_characters
            )
            call_number = metrics["ai_call_count"]

        client_setup_started = perf_counter()
        request_started = None
        output_characters = 0
        usage = {}
        status = None
        try:
            from google.genai import types

            client = self._client_for_request()
            client_setup_seconds = round(perf_counter() - client_setup_started, 3)
            request_started = perf_counter()
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(max_output_tokens=self.max_output_tokens),
            )
            status = _http_status(getattr(response, "sdk_http_response", None)) or 200
            raw_text = response.text or ""
            output_characters = len(raw_text)
            text = raw_text.strip()
            fence = chr(96) * 3
            if text.startswith(fence):
                text = text.split("\n", 1)[-1]
                if text.endswith(fence):
                    text = text[:-3]
            text = text.strip()
            usage = _usage_counts(response)
            duration = round(perf_counter() - request_started, 3)
            self._record_call_metrics(metrics, duration, output_characters, usage)
            self._log_request(
                metrics, call_number, input_characters, output_characters, duration,
                status, None, usage, client_setup_seconds
            )
            return text
        except Exception as error:
            duration = round(perf_counter() - request_started, 3) if request_started else 0.0
            status = _http_status(error) or status
            client_setup_seconds = round(perf_counter() - client_setup_started, 3)
            self._record_call_metrics(metrics, duration, output_characters, usage)
            self._log_request(
                metrics, call_number, input_characters, output_characters, duration,
                status, type(error).__name__, usage, client_setup_seconds
            )
            import httpx

            if isinstance(error, (httpx.TimeoutException, TimeoutError)) or status == 504:
                raise ApiError(
                    "AI_TIMEOUT",
                    "The AI service took too long to respond. Please retry, or try a shorter notice.",
                    504,
                ) from error
            if status in (400, 401, 403, 404):
                raise ApiError(
                    "AI_CONFIGURATION_ERROR",
                    "The AI service rejected the request. The administrator should check the API key, model access, and request configuration.",
                    503,
                ) from error
            if status == 429:
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

    @staticmethod
    def _record_call_metrics(metrics, duration, output_characters, usage):
        if metrics is None:
            return
        metrics["gemini_request_seconds"] = round(
            metrics.get("gemini_request_seconds", 0.0) + duration, 3
        )
        metrics["gemini_output_characters"] = (
            metrics.get("gemini_output_characters", 0) + output_characters
        )
        totals = metrics.setdefault("token_usage", {})
        for name, value in usage.items():
            if isinstance(value, (int, float)):
                totals[name] = totals.get(name, 0) + value

    def _log_request(
        self, metrics, call_number, input_characters, output_characters, duration,
        status, exception_type, usage, client_setup_seconds
    ):
        event = {
            "event": "gemini_generate_content",
            "request_id": metrics.get("request_id") if metrics else None,
            "call_number": call_number,
            "model": self.model,
            "genai_sdk_version": self.sdk_version,
            "http_status": status,
            "exception_type": exception_type,
            "input_characters": input_characters,
            "output_characters": output_characters,
            "request_seconds": duration,
            "client_setup_seconds": client_setup_seconds,
            "token_usage": usage,
            "max_output_tokens": self.max_output_tokens,
            "thinking_level_configured": None,
            "sdk_retry_options_configured": True,
            "ai_timeout_ms": self.timeout_ms,
            "sdk_retry_count": 0,
        }
        logger.info("fomuwise_ai_request %s", json.dumps(event, sort_keys=True))

    def generate_json(self, prompt):
        response_text = self._call(prompt)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            repair_started = perf_counter()
            repair_prompt = (
                "Convert the following response into valid JSON only. Preserve its data. "
                "Do not add facts. Return no markdown.\n\n" + response_text[:12000]
            )
            if self._metrics is not None:
                self._metrics["json_repair_used"] = True
                self._metrics["prompt_construction_seconds"] = round(
                    self._metrics.get("prompt_construction_seconds", 0.0)
                    + perf_counter()
                    - repair_started,
                    3,
                )
                self._metrics["repair_prompt_characters"] = len(repair_prompt)
            try:
                return json.loads(self._call(repair_prompt))
            except json.JSONDecodeError:
                raise ApiError(
                    "AI_OUTPUT_INVALID",
                    "The AI service returned an unusable response. Please retry.",
                    502,
                )
