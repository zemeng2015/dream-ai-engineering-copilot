# SPDX-License-Identifier: Apache-2.0

from dream.llm.base import LLMRequest, LLMResponse, prompt_text


class CustomLLMProvider:
    provider_name = "privatedemo-example-llm"
    model_name = "ExampleLLM"

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        prompt = prompt_text(prompt)
        preview = " ".join(prompt.split())[:120]
        return LLMResponse(
            text=f"PrivateDemo deterministic response for: {preview}",
            model_name=self.model_name,
            provider_name=self.provider_name,
            token_usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 6},
        )
