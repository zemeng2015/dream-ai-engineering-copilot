# SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dream.core.errors import ProviderConfigurationError, ProviderRequestError
from dream.llm.base import LLMResponse


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

    def complete(self, prompt: str) -> LLMResponse:
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
        data = self._post_json("/chat/completions", payload)
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
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderRequestError(
                f"OpenAI-compatible request failed with HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except URLError as exc:
            raise ProviderRequestError(
                f"OpenAI-compatible request failed: {exc.reason}"
            ) from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("OpenAI-compatible response was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ProviderRequestError("OpenAI-compatible response JSON was not an object.")
        return parsed

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
