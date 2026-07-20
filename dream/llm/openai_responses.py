# SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dream.core.errors import ProviderConfigurationError, ProviderRequestError
from dream.llm.base import LLMRequest, LLMResponse, prompt_text


class OpenAIResponsesProvider:
    """Native OpenAI Responses API provider for the Build Week GPT-5.6 path."""

    provider_name = "openai-responses"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        reasoning_effort: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip(
            "/"
        )
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-5.6-sol")
        self.reasoning_effort = reasoning_effort or os.getenv(
            "OPENAI_REASONING_EFFORT", "medium"
        )
        self.timeout_seconds = timeout_seconds or float(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ProviderConfigurationError(
                "OPENAI_API_KEY is required to use the GPT-5.6 Responses provider."
            )
        request_text = prompt_text(prompt)
        payload = {
            "model": self.model_name,
            "input": [
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are DREAM, a source-backed engineering copilot. "
                                "Produce reviewable engineering artifacts, preserve uncertainty, "
                                "and never claim that generated code is safe without validation."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": request_text}],
                },
            ],
            "reasoning": {"effort": self.reasoning_effort},
            "text": {"verbosity": "medium"},
        }
        data = self._post_json("/responses", payload)
        text = self._extract_output_text(data)
        if not text:
            raise ProviderRequestError("OpenAI Responses payload did not include output text.")
        return LLMResponse(
            text=text,
            model_name=str(data.get("model") or self.model_name),
            provider_name=self.provider_name,
            token_usage=self._token_usage(data.get("usage")),
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
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
                f"OpenAI Responses request failed with HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except URLError as exc:
            raise ProviderRequestError(f"OpenAI Responses request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ProviderRequestError(
                f"OpenAI Responses request timed out after {self.timeout_seconds:g} seconds."
            ) from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("OpenAI Responses response was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ProviderRequestError("OpenAI Responses response JSON was not an object.")
        return parsed

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        fragments: list[str] = []
        output = payload.get("output")
        if not isinstance(output, list):
            return ""
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                value = part.get("text")
                if isinstance(value, str) and part.get("type") in {"output_text", "text"}:
                    fragments.append(value)
        return "\n".join(fragments).strip()

    @staticmethod
    def _token_usage(usage: object) -> dict[str, int] | None:
        if not isinstance(usage, dict):
            return None
        values = {
            str(key): value
            for key, value in usage.items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
        return values or None
