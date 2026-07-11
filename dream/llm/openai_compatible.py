# SPDX-License-Identifier: Apache-2.0

import json
import os
from datetime import UTC, datetime
from hashlib import sha256
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from dream.core.errors import ProviderConfigurationError, ProviderRequestError
from dream.llm.base import LLMReceipt, LLMRequest, LLMResponse, prompt_text


class OpenAICompatibleProvider:
    provider_name = "openai-compatible"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("OPENAI_COMPATIBLE_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.base_url = base_url or os.getenv(
            "OPENAI_COMPATIBLE_BASE_URL", "https://api.openai.com/v1"
        )
        self.base_url = self.base_url.rstrip("/")
        self.model_name = model_name or os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4o-mini")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("OPENAI_COMPATIBLE_TIMEOUT_SECONDS", "30")
        )

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        prompt = prompt_text(prompt)
        if not self.api_key:
            raise ProviderConfigurationError(
                "OPENAI_COMPATIBLE_API_KEY or OPENAI_API_KEY is required to use "
                "OpenAICompatibleProvider."
            )
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are DREAM, a source-backed engineering copilot. "
                        "Return concise, reviewable engineering text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        payload.update(self._completion_parameters())
        data, receipt = self._post_json("/chat/completions", payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderRequestError(
                "OpenAI-compatible response did not include content."
            ) from exc
        usage = data.get("usage")
        token_usage = self._token_usage(usage)
        return LLMResponse(
            text=str(text),
            model_name=str(data.get("model") or self.model_name),
            provider_name=self.provider_name,
            token_usage=token_usage,
            receipt=receipt,
        )

    def _completion_parameters(self) -> dict[str, object]:
        return {}

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], LLMReceipt]:
        body = json.dumps(payload).encode("utf-8")
        requested_at = datetime.now(UTC)
        started = monotonic()
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        provider_request_id: str | None = None
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_bytes = response.read()
                provider_request_id = _provider_request_id(
                    getattr(response, "headers", None)
                )
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderRequestError(
                f"OpenAI-compatible request failed with HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except URLError as exc:
            raise ProviderRequestError(
                f"OpenAI-compatible request failed: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise ProviderRequestError(
                f"OpenAI-compatible request timed out after {self.timeout_seconds:g} seconds."
            ) from exc

        completed_at = datetime.now(UTC)
        raw = raw_bytes.decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("OpenAI-compatible response was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ProviderRequestError("OpenAI-compatible response JSON was not an object.")
        response_id = parsed.get("id")
        receipt = LLMReceipt(
            endpoint_host=urlparse(self.base_url).hostname or "unknown",
            request_sha256=sha256(body).hexdigest(),
            response_sha256=sha256(raw_bytes).hexdigest(),
            requested_at=requested_at.isoformat(),
            completed_at=completed_at.isoformat(),
            latency_ms=max(0, round((monotonic() - started) * 1000)),
            provider_request_id=provider_request_id,
            response_id=str(response_id) if response_id else None,
        )
        return parsed, receipt

    @staticmethod
    def _token_usage(usage: object) -> dict[str, int] | None:
        if not isinstance(usage, dict):
            return None
        token_usage = {
            str(key): value
            for key, value in usage.items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
        return token_usage or None


def _provider_request_id(headers: object) -> str | None:
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None
    for name in (
        "x-request-id",
        "x-acs-request-id",
        "x-dashscope-request-id",
        "request-id",
    ):
        value = getter(name)
        if value:
            return str(value)
    return None
