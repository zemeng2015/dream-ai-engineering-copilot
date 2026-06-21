# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    text: str
    model_name: str
    provider_name: str
    token_usage: dict[str, int] | None = Field(default=None)


class BaseLLMProvider(Protocol):
    provider_name: str
    model_name: str

    def complete(self, prompt: str) -> LLMResponse:
        """Return a completion for the supplied prompt."""

