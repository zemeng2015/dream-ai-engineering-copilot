# SPDX-License-Identifier: Apache-2.0

import math
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from dream.core.errors import DreamError, NotFoundError
from dream.experience.models import (
    ExperienceCaptureResult,
    ExperienceDecisionRecord,
    ExperienceFeedbackRequest,
    ExperienceMemory,
    ExperienceObservation,
    ExperiencePolicyResult,
    ExperienceRecallCandidate,
    ExperienceRecallRequest,
    ExperienceRecallResult,
)
from dream.experience.policy import ExperienceMemoryPolicy, RuleBasedExperienceMemoryPolicy
from dream.experience.repository import ExperienceMemoryRepository

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*", flags=re.IGNORECASE)
MAX_CONTEXT_VALUE_CHARS = 72


class ExperienceMemoryService:
    def __init__(
        self,
        *,
        repository: ExperienceMemoryRepository | None = None,
        policy: ExperienceMemoryPolicy | None = None,
    ) -> None:
        self.repository = repository or ExperienceMemoryRepository()
        self.policy = policy or RuleBasedExperienceMemoryPolicy()

    def capture(
        self,
        observation: ExperienceObservation,
        *,
        now: datetime | None = None,
    ) -> ExperienceCaptureResult:
        current = _utc(now)
        self._expire_due(observation.team_id, observation.user_id, current)
        active = self.repository.list_memories(
            team_id=observation.team_id,
            user_id=observation.user_id,
            include_inactive=False,
        )
        policy_result = self.policy.decide(observation, active)
        return self.apply_policy_result(observation, policy_result, now=current)

    def apply_policy_result(
        self,
        observation: ExperienceObservation,
        policy_result: ExperiencePolicyResult,
        *,
        now: datetime | None = None,
    ) -> ExperienceCaptureResult:
        current = _utc(now)
        proposal = policy_result.proposal
        requested_action = proposal.action
        action = proposal.action
        target: ExperienceMemory | None = None
        memory: ExperienceMemory | None = None
        affected: list[ExperienceMemory] = []

        active = self.repository.list_memories(
            team_id=observation.team_id,
            user_id=observation.user_id,
            include_inactive=False,
        )
        matching = self._matching_key(active, proposal.kind, proposal.key)

        if action == "remember" and matching:
            duplicate = next(
                (
                    item
                    for item in matching
                    if _normalize_value(item.value) == _normalize_value(proposal.value or "")
                ),
                None,
            )
            if duplicate:
                action = "ignore"
                target = duplicate
            else:
                action = "supersede"
                target = matching[0]
        elif action == "supersede":
            target = self._resolve_target(
                proposal.target_memory_id,
                matching,
                observation.team_id,
                observation.user_id,
            )
        elif action == "forget":
            target = self._resolve_target(
                proposal.target_memory_id,
                [],
                observation.team_id,
                observation.user_id,
            )

        if action in {"remember", "supersede"}:
            memory = self._new_memory(observation, policy_result, current)
            if action == "supersede" and target:
                target = target.model_copy(
                    update={
                        "status": "superseded",
                        "superseded_by": memory.memory_id,
                        "updated_at": current.isoformat(),
                    }
                )
                self.repository.save_memory(target)
                affected.append(target)
            self.repository.save_memory(memory)
            affected.append(memory)
        elif action == "forget" and target:
            target = target.model_copy(
                update={"status": "forgotten", "updated_at": current.isoformat()}
            )
            self.repository.save_memory(target)
            affected.append(target)

        rationale = proposal.rationale
        if requested_action == "remember" and action == "supersede":
            rationale += " Existing active memory with the same key was superseded."
        elif requested_action == "remember" and action == "ignore" and target:
            rationale += " An equivalent active memory already exists."

        decision = ExperienceDecisionRecord(
            decision_id=f"experience-decision-{uuid4().hex[:12]}",
            team_id=observation.team_id,
            user_id=observation.user_id,
            session_id=observation.session_id,
            requested_action=requested_action,
            action=action,
            target_memory_id=target.memory_id if target else proposal.target_memory_id,
            created_memory_id=memory.memory_id if memory else None,
            rationale=rationale,
            provider_name=policy_result.provider_name,
            model_name=policy_result.model_name,
            token_usage=policy_result.token_usage,
            llm_receipt=policy_result.llm_receipt,
            created_at=current.isoformat(),
        )
        self.repository.append_decision(decision)
        active_count = len(
            self.repository.list_memories(
                team_id=observation.team_id,
                user_id=observation.user_id,
                include_inactive=False,
            )
        )
        return ExperienceCaptureResult(
            decision=decision,
            memory=memory,
            affected_memories=affected,
            active_memory_count=active_count,
        )

    def recall(
        self,
        request: ExperienceRecallRequest,
        *,
        now: datetime | None = None,
    ) -> ExperienceRecallResult:
        current = _utc(now)
        expired_ids = self._expire_due(request.team_id, request.user_id, current)
        memories = self.repository.list_memories(
            team_id=request.team_id,
            user_id=request.user_id,
            include_inactive=False,
        )
        candidates = sorted(
            (self._candidate(memory, request.query, current) for memory in memories),
            key=lambda item: (-item.score, item.memory.memory_id),
        )[: request.limit]

        selected: list[ExperienceRecallCandidate] = []
        excluded: list[ExperienceRecallCandidate] = []
        used = 0
        for candidate in candidates:
            if used + candidate.estimated_tokens <= request.token_budget:
                chosen = candidate.model_copy(
                    update={"selected": True, "reason": f"{candidate.reason} Fits token budget."}
                )
                selected.append(chosen)
                used += candidate.estimated_tokens
            else:
                excluded.append(
                    candidate.model_copy(
                        update={
                            "reason": f"{candidate.reason} Excluded by token budget."
                        }
                    )
                )

        recalled_at = current.isoformat()
        for candidate in selected:
            updated = candidate.memory.model_copy(
                update={
                    "last_recalled_at": recalled_at,
                    "recall_count": candidate.memory.recall_count + 1,
                    "updated_at": recalled_at,
                }
            )
            self.repository.save_memory(updated)
            candidate.memory = updated

        return ExperienceRecallResult(
            team_id=request.team_id,
            user_id=request.user_id,
            session_id=request.session_id,
            query=request.query,
            token_budget=request.token_budget,
            estimated_tokens_used=used,
            selected=selected,
            excluded=excluded,
            expired_memory_ids=expired_ids,
            context_card=self._context_card(selected),
        )

    def record_feedback(self, request: ExperienceFeedbackRequest) -> ExperienceMemory:
        memory = self.repository.get_memory(request.memory_id)
        if memory.team_id != request.team_id or memory.user_id != request.user_id:
            raise NotFoundError(f"Experience memory not found: {request.memory_id}")
        updated = memory.model_copy(
            update={
                "feedback_count": memory.feedback_count + 1,
                "helpful_total": memory.helpful_total + (1 if request.helpful else -1),
                "correctness_total": memory.correctness_total + (1 if request.correct else -1),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        return self.repository.save_memory(updated)

    def list_memories(
        self,
        *,
        team_id: str,
        user_id: str,
        include_inactive: bool = True,
    ) -> list[ExperienceMemory]:
        return self.repository.list_memories(
            team_id=team_id,
            user_id=user_id,
            include_inactive=include_inactive,
        )

    def _new_memory(
        self,
        observation: ExperienceObservation,
        policy_result: ExperiencePolicyResult,
        current: datetime,
    ) -> ExperienceMemory:
        proposal = policy_result.proposal
        if not proposal.kind or not proposal.key or not proposal.value:
            raise DreamError("Memory action requires kind, key, and value.")
        valid_until = (
            (current + timedelta(days=proposal.ttl_days)).isoformat()
            if proposal.ttl_days
            else None
        )
        return ExperienceMemory(
            memory_id=f"experience-memory-{uuid4().hex[:12]}",
            team_id=observation.team_id,
            user_id=observation.user_id,
            kind=proposal.kind,
            key=_normalize_key(proposal.key),
            value=proposal.value.strip(),
            confidence=proposal.confidence,
            importance=proposal.importance,
            source_session_id=observation.session_id,
            source_reference=observation.source_reference
            or f"session:{observation.session_id}",
            created_at=current.isoformat(),
            updated_at=current.isoformat(),
            valid_from=current.isoformat(),
            valid_until=valid_until,
        )

    def _expire_due(self, team_id: str, user_id: str, current: datetime) -> list[str]:
        expired: list[str] = []
        for memory in self.repository.list_memories(
            team_id=team_id,
            user_id=user_id,
            include_inactive=False,
        ):
            if memory.valid_until and _parse_datetime(memory.valid_until) <= current:
                updated = memory.model_copy(
                    update={"status": "expired", "updated_at": current.isoformat()}
                )
                self.repository.save_memory(updated)
                expired.append(memory.memory_id)
        return expired

    @staticmethod
    def _matching_key(
        memories: list[ExperienceMemory],
        kind: str | None,
        key: str | None,
    ) -> list[ExperienceMemory]:
        if not kind or not key:
            return []
        normalized_key = _normalize_key(key)
        return sorted(
            [
                memory
                for memory in memories
                if memory.kind == kind and memory.key == normalized_key
            ],
            key=lambda memory: (memory.updated_at, memory.memory_id),
            reverse=True,
        )

    def _resolve_target(
        self,
        target_memory_id: str | None,
        matching: list[ExperienceMemory],
        team_id: str,
        user_id: str,
    ) -> ExperienceMemory:
        target = self.repository.get_memory(target_memory_id) if target_memory_id else None
        if target is None and matching:
            target = matching[0]
        if (
            target is None
            or target.team_id != team_id
            or target.user_id != user_id
            or target.status != "active"
        ):
            raise DreamError("Memory action target must be an active memory in the same scope.")
        return target

    @staticmethod
    def _candidate(
        memory: ExperienceMemory,
        query: str,
        current: datetime,
    ) -> ExperienceRecallCandidate:
        query_terms = set(_tokens(query))
        memory_terms = set(_tokens(f"{memory.kind} {memory.key} {memory.value}"))
        overlap = len(query_terms & memory_terms) / max(1, len(query_terms))
        age_days = max(0.0, (current - _parse_datetime(memory.updated_at)).total_seconds() / 86400)
        recency = 1.0 / (1.0 + age_days / 30.0)
        feedback = (
            (memory.helpful_total + memory.correctness_total) / (2 * memory.feedback_count)
            if memory.feedback_count
            else 0.0
        )
        kind_bonus = {"preference": 1.5, "policy": 1.2, "episode": 0.6}[memory.kind]
        score = round(
            6.0 * overlap
            + 0.8 * memory.importance
            + 1.5 * memory.confidence
            + recency
            + 1.5 * feedback
            + kind_bonus,
            4,
        )
        context_value = _compact_context_value(memory.value)
        estimated_tokens = max(
            8,
            math.ceil((len(memory.kind) + len(memory.key) + len(context_value)) / 4)
            + 4,
        )
        return ExperienceRecallCandidate(
            memory=memory,
            score=score,
            estimated_tokens=estimated_tokens,
            selected=False,
            reason=(
                f"overlap={overlap:.2f}; importance={memory.importance}; "
                f"confidence={memory.confidence:.2f}; feedback={feedback:.2f}."
            ),
        )

    @staticmethod
    def _context_card(selected: list[ExperienceRecallCandidate]) -> str:
        if not selected:
            return "No active experience memories fit this request and token budget."
        lines = ["# DREAM Experience Memory Context", ""]
        for item in selected:
            memory = item.memory
            lines.append(
                f"- {memory.kind}:{memory.key} = "
                f"{_compact_context_value(memory.value)}"
            )
        return "\n".join(lines).rstrip() + "\n"


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _utc(parsed)


def _normalize_key(value: str) -> str:
    tokens = _tokens(value)
    if not tokens:
        raise DreamError("Memory key must contain letters or numbers.")
    return "_".join(tokens)


def _normalize_value(value: str) -> str:
    return " ".join(value.lower().split())


def _compact_context_value(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= MAX_CONTEXT_VALUE_CHARS:
        return normalized
    shortened = normalized[: MAX_CONTEXT_VALUE_CHARS - 3].rsplit(" ", 1)[0]
    return f"{shortened or normalized[: MAX_CONTEXT_VALUE_CHARS - 3]}..."


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value)]
