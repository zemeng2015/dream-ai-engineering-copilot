# SPDX-License-Identifier: Apache-2.0

from dream.llm.base import LLMResponse


class MockLLMProvider:
    provider_name = "mock"
    model_name = "mock-deterministic-v1"

    def complete(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            text=prompt,
            model_name=self.model_name,
            provider_name=self.provider_name,
            token_usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 0},
        )

