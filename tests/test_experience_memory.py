# SPDX-License-Identifier: Apache-2.0

from datetime import UTC, datetime, timedelta

from dream.experience import (
    ExperienceFeedbackRequest,
    ExperienceMemoryRepository,
    ExperienceMemoryService,
    ExperienceObservation,
    ExperiencePolicyResult,
    ExperienceRecallRequest,
    LLMExperienceMemoryPolicy,
    MemoryActionProposal,
)
from dream.llm.base import LLMResponse


class StaticPolicy:
    def __init__(self, proposal: MemoryActionProposal) -> None:
        self.proposal = proposal

    def decide(self, observation, active_memories) -> ExperiencePolicyResult:
        return ExperiencePolicyResult(
            proposal=self.proposal,
            provider_name="test-policy",
            model_name="test-memory-curator",
        )


class FakeQwenProvider:
    provider_name = "qwen-cloud"
    model_name = "qwen3.7-plus"

    def complete(self, prompt) -> LLMResponse:
        assert "Memory Curator" in str(prompt)
        return LLMResponse(
            text="""```json
{
  "action": "remember",
  "kind": "preference",
  "key": "production_retry_mode",
  "value": "retry only failed tasks",
  "target_memory_id": null,
  "confidence": 0.94,
  "importance": 5,
  "ttl_days": null,
  "rationale": "Durable user preference for production retries."
}
```""",
            provider_name=self.provider_name,
            model_name=self.model_name,
            token_usage={"total_tokens": 180},
        )


def _observation(session_id: str, text: str) -> ExperienceObservation:
    return ExperienceObservation(
        team_id="demo_team",
        user_id="zack",
        session_id=session_id,
        observation=text,
        source_reference=f"session:{session_id}",
    )


def _remember(
    *,
    key: str,
    value: str,
    kind: str = "preference",
    importance: int = 4,
    ttl_days: int | None = None,
) -> MemoryActionProposal:
    return MemoryActionProposal(
        action="remember",
        kind=kind,
        key=key,
        value=value,
        confidence=0.9,
        importance=importance,
        ttl_days=ttl_days,
        rationale="Test memory action.",
    )


def test_experience_memory_persists_across_service_instances(tmp_path) -> None:
    db_path = tmp_path / "experience.sqlite"
    first = ExperienceMemoryService(
        repository=ExperienceMemoryRepository(db_path),
        policy=StaticPolicy(
            _remember(key="production_retry_mode", value="retry only failed tasks")
        ),
    )
    captured = first.capture(
        _observation("session-1", "For production, retry only failed tasks."),
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )

    second = ExperienceMemoryService(repository=ExperienceMemoryRepository(db_path))
    recalled = second.recall(
        ExperienceRecallRequest(
            team_id="demo_team",
            user_id="zack",
            session_id="session-2",
            query="How should production retries run?",
            token_budget=128,
        ),
        now=datetime(2026, 7, 11, tzinfo=UTC),
    )

    assert captured.decision.action == "remember"
    assert captured.memory is not None
    assert [item.memory.memory_id for item in recalled.selected] == [
        captured.memory.memory_id
    ]
    assert "retry only failed tasks" in recalled.context_card


def test_conflicting_preference_automatically_supersedes_old_memory(tmp_path) -> None:
    repository = ExperienceMemoryRepository(tmp_path / "experience.sqlite")
    first = ExperienceMemoryService(
        repository=repository,
        policy=StaticPolicy(
            _remember(key="production_retry_mode", value="retry all tasks")
        ),
    ).capture(
        _observation("session-1", "Retry all tasks."),
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )
    second = ExperienceMemoryService(
        repository=repository,
        policy=StaticPolicy(
            _remember(key="production_retry_mode", value="retry only failed tasks")
        ),
    ).capture(
        _observation("session-2", "New policy: retry only failed tasks."),
        now=datetime(2026, 7, 11, tzinfo=UTC),
    )

    memories = repository.list_memories(
        team_id="demo_team", user_id="zack", include_inactive=True
    )
    old = next(memory for memory in memories if memory.memory_id == first.memory.memory_id)
    active = [memory for memory in memories if memory.status == "active"]

    assert second.decision.requested_action == "remember"
    assert second.decision.action == "supersede"
    assert old.status == "superseded"
    assert old.superseded_by == second.memory.memory_id
    assert [memory.value for memory in active] == ["retry only failed tasks"]


def test_expired_memory_never_leaks_into_recall(tmp_path) -> None:
    repository = ExperienceMemoryRepository(tmp_path / "experience.sqlite")
    captured = ExperienceMemoryService(
        repository=repository,
        policy=StaticPolicy(
            _remember(
                key="temporary_release_window",
                value="deploy after 18:00 UTC",
                kind="policy",
                ttl_days=1,
            )
        ),
    ).capture(
        _observation("session-1", "This release window is valid for one day."),
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )

    recalled = ExperienceMemoryService(repository=repository).recall(
        ExperienceRecallRequest(
            team_id="demo_team",
            user_id="zack",
            session_id="session-3",
            query="When should we deploy?",
            token_budget=128,
        ),
        now=datetime(2026, 7, 12, tzinfo=UTC),
    )

    assert captured.memory.memory_id in recalled.expired_memory_ids
    assert recalled.selected == []
    assert repository.get_memory(captured.memory.memory_id).status == "expired"


def test_recall_prioritizes_critical_memory_under_token_budget(tmp_path) -> None:
    repository = ExperienceMemoryRepository(tmp_path / "experience.sqlite")
    current = datetime(2026, 7, 10, tzinfo=UTC)
    critical = ExperienceMemoryService(
        repository=repository,
        policy=StaticPolicy(
            _remember(
                key="production_retry_safety",
                value="ask for approval",
                kind="policy",
                importance=5,
            )
        ),
    ).capture(_observation("session-1", "Ask before production retry."), now=current)
    ExperienceMemoryService(
        repository=repository,
        policy=StaticPolicy(
            _remember(
                key="retry_background_notes",
                value="background " * 120,
                kind="episode",
                importance=1,
            )
        ),
    ).capture(
        _observation("session-2", "Long low-priority retry notes."),
        now=current + timedelta(minutes=1),
    )

    recalled = ExperienceMemoryService(repository=repository).recall(
        ExperienceRecallRequest(
            team_id="demo_team",
            user_id="zack",
            session_id="session-3",
            query="production retry safety",
            token_budget=40,
        ),
        now=current + timedelta(days=1),
    )

    assert [item.memory.memory_id for item in recalled.selected] == [
        critical.memory.memory_id
    ]
    assert recalled.estimated_tokens_used <= recalled.token_budget
    assert any("token budget" in item.reason for item in recalled.excluded)


def test_feedback_changes_future_recall_ranking(tmp_path) -> None:
    repository = ExperienceMemoryRepository(tmp_path / "experience.sqlite")
    current = datetime(2026, 7, 10, tzinfo=UTC)
    memories = []
    for index, value in enumerate(["ask operator", "ask service owner"], start=1):
        result = ExperienceMemoryService(
            repository=repository,
            policy=StaticPolicy(
                _remember(key=f"retry_escalation_{index}", value=value, importance=3)
            ),
        ).capture(
            _observation(f"session-{index}", value),
            now=current + timedelta(minutes=index),
        )
        memories.append(result.memory)

    service = ExperienceMemoryService(repository=repository)
    for _ in range(2):
        service.record_feedback(
            ExperienceFeedbackRequest(
                team_id="demo_team",
                user_id="zack",
                memory_id=memories[0].memory_id,
                helpful=True,
                correct=True,
            )
        )
        service.record_feedback(
            ExperienceFeedbackRequest(
                team_id="demo_team",
                user_id="zack",
                memory_id=memories[1].memory_id,
                helpful=False,
                correct=False,
            )
        )

    recalled = service.recall(
        ExperienceRecallRequest(
            team_id="demo_team",
            user_id="zack",
            session_id="session-3",
            query="retry escalation",
            token_budget=256,
        ),
        now=current + timedelta(days=1),
    )

    assert recalled.selected[0].memory.memory_id == memories[0].memory_id
    assert recalled.selected[0].score > recalled.selected[1].score


def test_qwen_memory_policy_parses_fenced_structured_action() -> None:
    result = LLMExperienceMemoryPolicy(FakeQwenProvider()).decide(
        _observation("session-1", "Always retry only failed production tasks."),
        [],
    )

    assert result.provider_name == "qwen-cloud"
    assert result.model_name == "qwen3.7-plus"
    assert result.proposal.action == "remember"
    assert result.proposal.kind == "preference"
    assert result.proposal.importance == 5
    assert result.token_usage == {"total_tokens": 180}

