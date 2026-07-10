# SPDX-License-Identifier: Apache-2.0

import os
from urllib.parse import urlparse

from dream.core.errors import ProviderConfigurationError, ProviderRequestError
from dream.llm.base import LLMRequest, LLMResponse, prompt_text
from dream.llm.openai_compatible import OpenAICompatibleProvider

QWEN_CLOUD_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
QWEN_CLOUD_DEFAULT_MODEL = "qwen3.7-plus"


class QwenCloudProvider(OpenAICompatibleProvider):
    provider_name = "qwen-cloud"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        qwen_api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        qwen_base_url = (
            base_url
            or os.getenv("QWEN_BASE_URL")
            or os.getenv("DASHSCOPE_BASE_URL")
            or QWEN_CLOUD_BASE_URL
        )
        _validate_qwen_base_url(qwen_base_url)
        super().__init__(
            api_key=qwen_api_key,
            base_url=qwen_base_url,
            model_name=model_name or os.getenv("QWEN_MODEL") or QWEN_CLOUD_DEFAULT_MODEL,
            timeout_seconds=timeout_seconds or float(os.getenv("QWEN_TIMEOUT_SECONDS", "30")),
        )
        self.api_key = qwen_api_key
        self.enable_thinking = _boolean_env("QWEN_ENABLE_THINKING", default=False)
        self.max_completion_tokens = _positive_int_env("QWEN_MAX_COMPLETION_TOKENS")

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ProviderConfigurationError(
                "DASHSCOPE_API_KEY or QWEN_API_KEY is required to use QwenCloudProvider."
            )
        prompt_value = prompt_text(prompt)
        max_chars = _positive_int_env("QWEN_MAX_PROMPT_CHARS")
        if max_chars and len(prompt_value) > max_chars:
            raise ProviderRequestError(
                f"Qwen prompt exceeds the configured {max_chars}-character public demo limit."
            )
        return super().complete(prompt_value)

    def _completion_parameters(self) -> dict[str, object]:
        parameters: dict[str, object] = {"enable_thinking": self.enable_thinking}
        if self.max_completion_tokens:
            parameters["max_tokens"] = self.max_completion_tokens
        return parameters


def _positive_int_env(name: str) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return 0
    try:
        value = int(raw)
    except ValueError as exc:
        raise ProviderConfigurationError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise ProviderConfigurationError(f"{name} must be a positive integer.")
    return value


def _boolean_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ProviderConfigurationError(f"{name} must be true or false.")


def _validate_qwen_base_url(value: str) -> None:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError as exc:
        raise ProviderConfigurationError("Qwen base URL is invalid.") from exc

    host = (parsed.hostname or "").lower()
    shared_hosts = {"dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com"}
    workspace_suffix = ".ap-southeast-1.maas.aliyuncs.com"
    workspace_name = host.removesuffix(workspace_suffix)
    workspace_host = (
        host.endswith(workspace_suffix)
        and bool(workspace_name)
        and all(char.islower() or char.isdigit() or char == "-" for char in workspace_name)
    )
    valid = (
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and port in {None, 443}
        and (host in shared_hosts or workspace_host)
        and parsed.path.rstrip("/") == "/compatible-mode/v1"
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )
    if not valid:
        raise ProviderConfigurationError(
            "Qwen base URL must use an allowlisted Alibaba Model Studio endpoint."
        )
