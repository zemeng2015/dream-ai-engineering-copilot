# SPDX-License-Identifier: Apache-2.0

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from dream.core.errors import ProviderConfigurationError, ProviderRequestError
from dream.llm.openai_compatible import OpenAICompatibleProvider


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
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


def test_openai_compatible_provider_never_follows_redirect() -> None:
    sink_hits: list[str] = []

    class SinkHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            sink_hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, format, *args):  # noqa: ANN001, A002
            return

    sink = ThreadingHTTPServer(("127.0.0.1", 0), SinkHandler)

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self.send_response(302)
            self.send_header(
                "Location",
                f"http://127.0.0.1:{sink.server_port}/stolen",
            )
            self.end_headers()

        def log_message(self, format, *args):  # noqa: ANN001, A002
            return

    redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    threads = [
        Thread(target=server.serve_forever, daemon=True) for server in [sink, redirect]
    ]
    for thread in threads:
        thread.start()
    try:
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url=f"http://127.0.0.1:{redirect.server_port}/v1",
            model_name="demo-model",
        )
        with pytest.raises(ProviderRequestError, match="redirect"):
            provider.complete("never forward this prompt")
    finally:
        redirect.shutdown()
        sink.shutdown()
        redirect.server_close()
        sink.server_close()

    assert sink_hits == []


def test_openai_compatible_provider_does_not_echo_http_error_body() -> None:
    secret_error_body = "provider-returned-sensitive-debug-payload"

    class ErrorHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self.send_response(400)
            self.end_headers()
            self.wfile.write(secret_error_body.encode())

        def log_message(self, format, *args):  # noqa: ANN001, A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ErrorHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model_name="demo-model",
        )
        with pytest.raises(ProviderRequestError) as error:
            provider.complete("safe prompt")
    finally:
        server.shutdown()
        server.server_close()

    assert "HTTP 400" in str(error.value)
    assert secret_error_body not in str(error.value)
