# SPDX-License-Identifier: Apache-2.0

import json

import pytest

from dream.core.errors import ProviderConfigurationError
from dream.llm.openai_compatible import OpenAICompatibleProvider


class FakeResponse:
    headers = {"x-request-id": "req-openai-compatible-123"}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "id": "chatcmpl-test-123",
                "model": "demo-model",
                "choices": [{"message": {"content": "DREAM_OK source-backed"}}],
                "usage": {
                    "prompt_tokens": 4,
                    "completion_tokens": 3,
                    "prompt_tokens_details": {"cached_tokens": 0},
                },
            }
        ).encode("utf-8")


def test_openai_compatible_provider_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    provider = OpenAICompatibleProvider()

    with pytest.raises(ProviderConfigurationError):
        provider.complete("hello")


def test_openai_compatible_provider_uses_openai_key_fallback(monkeypatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("dream.llm.openai_compatible.urlopen", fake_urlopen)

    response = OpenAICompatibleProvider(model_name="demo-model", timeout_seconds=5).complete(
        "Return DREAM_OK"
    )

    assert response.text == "DREAM_OK source-backed"
    assert response.model_name == "demo-model"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["timeout"] == 5
    assert captured["payload"]["model"] == "demo-model"
    assert response.token_usage == {"prompt_tokens": 4, "completion_tokens": 3}
    assert response.receipt is not None
    assert response.receipt.endpoint_host == "api.openai.com"
    assert response.receipt.provider_request_id == "req-openai-compatible-123"
    assert response.receipt.response_id == "chatcmpl-test-123"
    assert len(response.receipt.request_sha256) == 64
    assert len(response.receipt.response_sha256) == 64
    assert response.receipt.latency_ms >= 0
