# SPDX-License-Identifier: Apache-2.0

import json

import pytest

from dream.core.errors import ProviderConfigurationError
from dream.llm.qwen_cloud import QWEN_CLOUD_BASE_URL, QwenCloudProvider


class FakeQwenResponse:
    def __enter__(self) -> "FakeQwenResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "model": "qwen3.7-plus",
                "choices": [{"message": {"content": "DREAM_QWEN_OK governed memory"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 5},
            }
        ).encode("utf-8")


def test_qwen_cloud_provider_requires_qwen_key(monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "not-a-qwen-key")
    monkeypatch.setenv("OPENAI_API_KEY", "also-not-a-qwen-key")

    provider = QwenCloudProvider()

    with pytest.raises(ProviderConfigurationError):
        provider.complete("hello")


def test_qwen_cloud_provider_uses_dashscope_endpoint(monkeypatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-qwen-key")

    def fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["auth"] = request.headers["Authorization"]
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeQwenResponse()

    monkeypatch.setattr("dream.llm.openai_compatible.urlopen", fake_urlopen)

    response = QwenCloudProvider(timeout_seconds=6).complete("Return DREAM_QWEN_OK")

    assert response.provider_name == "qwen-cloud"
    assert response.model_name == "qwen3.7-plus"
    assert response.text == "DREAM_QWEN_OK governed memory"
    assert captured["url"] == f"{QWEN_CLOUD_BASE_URL}/chat/completions"
    assert captured["auth"] == "Bearer test-qwen-key"
    assert captured["timeout"] == 6
    assert captured["payload"]["model"] == "qwen3.7-plus"
    assert response.token_usage == {"prompt_tokens": 7, "completion_tokens": 5}
