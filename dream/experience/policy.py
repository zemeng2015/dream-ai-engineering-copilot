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
            payload = json.loads(_extract_json_object(response.text))
            proposal = MemoryActionProposal.model_validate(
                _normalize_proposal_payload(payload)
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
            llm_receipt=response.receipt,
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
- Use preference for a person's durable defaults ("I prefer", "my preference",
  "for me"); use policy for mandatory team or organization rules; use episode for a
  reusable lesson learned from an observed outcome.
- Store explicit temporary operational directives when they affect later decisions, and
  set ttl_days from the stated duration so they expire automatically.
- Do not store secrets, transient chatter, or unsupported assumptions.
- Use supersede when the same key has a newer conflicting value; reuse the exact active
  memory key and target_memory_id.
- Use forget only when the observation explicitly invalidates an existing memory.
- Keep keys short and stable snake_case without team, user, or company-name prefixes.
- Keep values as concise natural-language phrases, never snake_case. Preserve units such
  as percent, workers, days, minutes, region, and UTC when they affect meaning.
- First-person choices such as "I prefer" or "I want" are preferences.
- Organization-wide must/should rules are policies.
- Repeated lessons or explicitly reusable tips are episodes, even at importance 1.
- Importance must always be an integer from 1 to 5, including ignore and forget.
- TTL days must be null or an integer from 1 to 3650; use null for no expiry.
- Return one JSON object and no markdown.

Decision examples:
- "For today only, route alerts to the response room" means remember a policy with
  ttl_days 1; it is not transient chatter because it affects a later decision.
- "Reviews repeatedly go faster when graphs are grouped by service; keep this reusable
  tip" means remember an episode with importance 1.
- "The build took 94 seconds" means ignore because it is a one-off observation.

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


def _normalize_proposal_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    if isinstance(normalized.get("action"), str):
        normalized["action"] = normalized["action"].strip().lower()
    if isinstance(normalized.get("kind"), str):
        normalized["kind"] = normalized["kind"].strip().lower() or None
    for field in ("key", "value", "target_memory_id"):
        if isinstance(normalized.get(field), str) and not normalized[field].strip():
            normalized[field] = None
    if normalized.get("action") in {"ignore", "forget"} and normalized.get(
        "importance"
    ) in {None, 0, "0"}:
        normalized["importance"] = 1
    if normalized.get("ttl_days") in {0, "0", ""}:
        normalized["ttl_days"] = None
    return normalized


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
