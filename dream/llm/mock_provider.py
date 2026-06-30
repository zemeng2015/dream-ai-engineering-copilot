# SPDX-License-Identifier: Apache-2.0

import re

from dream.llm.base import LLMRequest, LLMResponse, prompt_text


class MockLLMProvider:
    provider_name = "mock"
    model_name = "mock-deterministic-v1"

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        prompt = prompt_text(prompt)
        return LLMResponse(
            text=_redact_secret_like_values(prompt),
            model_name=self.model_name,
            provider_name=self.provider_name,
            token_usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 0},
        )


_SECRET_VALUE_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|password|passwd|token)(\s*[:=]\s*)([^\s,;\"']+)"
)


def _redact_secret_like_values(text: str) -> str:
    return _SECRET_VALUE_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        text,
    )
