import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest

from app.errors import ApiError
from app.services.gemma_service import GemmaService


def service_with_responses(*responses):
    service = GemmaService("private-test-key", "test-model")
    generate = Mock(side_effect=responses)
    service._client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    return service, generate


def test_sdk_timeout_and_single_attempt():
    service = GemmaService("private-test-key", "test-model")
    with patch("google.genai.Client") as client:
        service._client_for_request()
        options = client.call_args.kwargs["http_options"]
        assert options.timeout == 40000
        assert options.retry_options.attempts == 1


@pytest.mark.parametrize("timeout", [0, 999, 45001])
def test_timeout_budget_cannot_exceed_worker_budget(timeout):
    with pytest.raises(ValueError):
        GemmaService("key", "model", timeout_ms=timeout)


def test_timeout_is_actionable_and_logged_without_secrets(caplog):
    service, generate = service_with_responses(httpx.ReadTimeout("sensitive provider detail"))
    with caplog.at_level(logging.INFO, logger="app.services.gemma_service"):
        with pytest.raises(ApiError) as caught:
            service.generate_json("private PDF contents")
    assert caught.value.code == "AI_TIMEOUT"
    assert caught.value.status == 504
    assert generate.call_count == 1
    event = json.loads(caplog.records[-1].message.split(" ", 1)[1])
    assert event["exception_type"] == "ReadTimeout"
    assert event["ai_timeout_ms"] == 40000
    assert event["sdk_retry_options_configured"] is True
    assert "private-test-key" not in caplog.text
    assert "private PDF contents" not in caplog.text
    assert "sensitive provider detail" not in caplog.text


@pytest.mark.parametrize("status,code", [(400, "AI_CONFIGURATION_ERROR"), (401, "AI_CONFIGURATION_ERROR"), (403, "AI_CONFIGURATION_ERROR"), (404, "AI_CONFIGURATION_ERROR"), (429, "AI_RATE_LIMITED"), (503, "AI_UNAVAILABLE")])
def test_provider_errors_are_classified(status, code):
    error = RuntimeError("provider failure")
    error.code = status
    service, _ = service_with_responses(error)
    with pytest.raises(ApiError) as caught:
        service.generate_json("prompt")
    assert caught.value.code == code


def test_repair_timeout_keeps_timeout_error():
    service, generate = service_with_responses(SimpleNamespace(text="invalid JSON"), httpx.ReadTimeout("slow"))
    with pytest.raises(ApiError) as caught:
        service.generate_json("prompt")
    assert caught.value.code == "AI_TIMEOUT"
    assert generate.call_count == 2


def test_repair_is_limited_to_one_extra_call():
    service, generate = service_with_responses(SimpleNamespace(text="invalid"), SimpleNamespace(text="still invalid"))
    with pytest.raises(ApiError) as caught:
        service.generate_json("prompt")
    assert caught.value.code == "AI_OUTPUT_INVALID"
    assert generate.call_count == 2


def test_valid_response_does_not_need_repair():
    service, generate = service_with_responses(SimpleNamespace(text='{"summary": "ok"}'))
    assert service.generate_json("prompt") == {"summary": "ok"}
    assert generate.call_count == 1
