# SPDX-License-Identifier: Apache-2.0

from dream.dlp.engine import DefaultDlpEngine
from dream.llm.base import BaseLLMProvider, LLMRequest, LLMResponse, prompt_text


class DlpGuardedLLMProvider:
    """Screen every model prompt and response without changing provider identity."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        *,
        dlp_engine: DefaultDlpEngine | None = None,
    ) -> None:
        self.provider = provider
        self.dlp_engine = dlp_engine or DefaultDlpEngine()
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        metadata = prompt.metadata if isinstance(prompt, LLMRequest) else {}
        team_id = metadata.get("team_id", "_unknown")
        resource_id = (
            metadata.get("resource_id")
            or metadata.get("run_id")
            or metadata.get("evaluation_id")
            or metadata.get("use_case")
            or "llm-prompt"
        )
        classification = metadata.get("classification", "internal")
        prompt_inspection = self.dlp_engine.enforce(
            prompt_text(prompt),
            stage="pre_prompt",
            team_id=team_id,
            resource_id=resource_id,
            classification=classification,
        )
        response = self.provider.complete(prompt_inspection.sanitized_text)
        response_inspection = self.dlp_engine.enforce(
            response.text,
            stage="post_response",
            team_id=team_id,
            resource_id=resource_id,
            classification=classification,
        )
        return response.model_copy(update={"text": response_inspection.sanitized_text})


def ensure_dlp_guarded_provider(
    provider: BaseLLMProvider,
    *,
    dlp_engine: DefaultDlpEngine | None = None,
) -> DlpGuardedLLMProvider:
    if isinstance(provider, DlpGuardedLLMProvider):
        return provider
    return DlpGuardedLLMProvider(provider, dlp_engine=dlp_engine)
