# SPDX-License-Identifier: Apache-2.0

import json
from typing import Protocol

from dream.core.errors import ProviderRequestError
from dream.experience.models import (
    ExperienceMemory,
    ExperienceObservation,
    ExperiencePolicyResult,
    MemoryActionProposal,
)
from dream.llm.base import BaseLLMProvider


class ExperienceMemoryPolicy(Protocol):
    def decide(
        self,
        observation: ExperienceObservation,
        active_memories: list[ExperienceMemory],
    ) -> ExperiencePolicyResult: ...


class LLMExperienceMemoryPolicy:
    def __init__(self, provider: BaseLLMProvider) -> None:
        self.provider = provider

    def decide(
        self,
        observation: ExperienceObservation,
        active_memories: list[ExperienceMemory],
    ) -> ExperiencePolicyResult:
        response = self.provider.complete(self._prompt(observation, active_memories))
        try:
            proposal = MemoryActionProposal.model_validate(
                json.loads(_extract_json_object(response.text))
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderRequestError(
                "Memory policy response was not a valid action JSON object."
            ) from exc
        _validate_proposal(proposal)
        return ExperiencePolicyResult(
            proposal=proposal,
            provider_name=response.provider_name,
            model_name=response.model_name,
            token_usage=response.token_usage,
        )

    @staticmethod
    def _prompt(
        observation: ExperienceObservation,
        active_memories: list[ExperienceMemory],
    ) -> str:
        memories = [
            {
                "memory_id": memory.memory_id,
                "kind": memory.kind,
                "key": memory.key,
                "value": memory.value,
                "confidence": memory.confidence,
                "importance": memory.importance,
                "valid_until": memory.valid_until,
            }
            for memory in active_memories[:24]
        ]
        return f"""You are DREAM's Memory Curator. Decide whether the new observation should
be remembered, supersede an existing memory, forget an existing memory, or be ignored.

Safety rules:
- Store only durable preferences, operating policies, or reusable experience.
- Do not store secrets, transient chatter, or unsupported assumptions.
- Use supersede when the same key has a newer conflicting value.
- Use forget only when the observation explicitly invalidates an existing memory.
- Keep keys short and stable snake_case.
- Return one JSON object and no markdown.

JSON contract:
{{
  "action": "remember|supersede|forget|ignore",
  "kind": "preference|policy|episode|null",
  "key": "string|null",
  "value": "string|null",
  "target_memory_id": "string|null",
  "confidence": 0.0,
  "importance": 1,
  "ttl_days": null,
  "rationale": "short explanation"
}}

Team: {observation.team_id}
User: {observation.user_id}
Session: {observation.session_id}
Source: {observation.source_reference or f"session:{observation.session_id}"}
Observation:
{observation.observation}

Active memories:
{json.dumps(memories, ensure_ascii=True)}
"""


class RuleBasedExperienceMemoryPolicy:
    """Conservative offline policy for tests and local recovery flows."""

    provider_name = "deterministic-memory-policy"
    model_name = "experience-policy-v1"

    def decide(
        self,
        observation: ExperienceObservation,
        active_memories: list[ExperienceMemory],
    ) -> ExperiencePolicyResult:
        text = observation.observation.strip()
        prefix, separator, remainder = text.partition(":")
        normalized_prefix = prefix.strip().lower()
        if normalized_prefix == "forget" and separator:
            proposal = MemoryActionProposal(
                action="forget",
                target_memory_id=remainder.strip(),
                rationale="Explicit deterministic forget instruction.",
            )
        elif normalized_prefix in {"preference", "policy", "episode"} and separator:
            key, equals, value = remainder.partition("=")
            if equals and key.strip() and value.strip():
                proposal = MemoryActionProposal(
                    action="remember",
                    kind=normalized_prefix,
                    key=key.strip(),
                    value=value.strip(),
                    rationale="Explicit structured memory instruction.",
                )
            else:
                proposal = _ignore("Structured memory instruction was incomplete.")
        else:
            proposal = _ignore("Offline policy stores only explicit structured instructions.")
        _validate_proposal(proposal)
        return ExperiencePolicyResult(
            proposal=proposal,
            provider_name=self.provider_name,
            model_name=self.model_name,
        )


def _ignore(rationale: str) -> MemoryActionProposal:
    return MemoryActionProposal(action="ignore", rationale=rationale)


def _validate_proposal(proposal: MemoryActionProposal) -> None:
    if proposal.action in {"remember", "supersede"}:
        if not proposal.kind or not proposal.key or not proposal.value:
            raise ValueError("Remember and supersede actions require kind, key, and value.")
    if proposal.action == "forget" and not proposal.target_memory_id:
        raise ValueError("Forget action requires target_memory_id.")


def _extract_json_object(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object was found.")
    return text[start : end + 1]

