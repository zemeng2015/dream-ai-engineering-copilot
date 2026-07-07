# SPDX-License-Identifier: Apache-2.0

import os

from dream.core.errors import ProviderConfigurationError
from dream.llm.base import LLMRequest, LLMResponse
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
        super().__init__(
            api_key=qwen_api_key,
            base_url=(
                base_url
                or os.getenv("QWEN_BASE_URL")
                or os.getenv("DASHSCOPE_BASE_URL")
                or QWEN_CLOUD_BASE_URL
            ),
            model_name=model_name or os.getenv("QWEN_MODEL") or QWEN_CLOUD_DEFAULT_MODEL,
            timeout_seconds=timeout_seconds or float(os.getenv("QWEN_TIMEOUT_SECONDS", "30")),
        )
        self.api_key = qwen_api_key

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ProviderConfigurationError(
                "DASHSCOPE_API_KEY or QWEN_API_KEY is required to use QwenCloudProvider."
            )
        return super().complete(prompt)
