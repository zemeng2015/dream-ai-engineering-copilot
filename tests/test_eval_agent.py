# SPDX-License-Identifier: Apache-2.0

import json

from fastapi.testclient import TestClient

from dream.api.app import create_app
from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.core.paths import display_path, ensure_artifacts_dir
from dream.evals.evaluator import EvaluationAgent
from dream.evals.evidence import EvalProfileLoader, EvidenceCoverageAnalyzer
from dream.evals.models import EvaluationRequest
from dream.evals.repository import EvaluationRepository
from dream.llm import LLMResponse


class FakeJudgeLLMProvider:
    provider_name = "fake-judge"
    model_name = "fake-judge-model"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete(self, prompt) -> LLMResponse:
        text = prompt.prompt if hasattr(prompt, "prompt") else str(prompt)
        self.prompts.append(text)
        return LLMResponse(
            text=json.dumps(
                {
                    "summary": "The draft is grounded but still needs human answers.",
                    "readiness": "needs_review",
                    "confidence": 0.82,
                    "risks": ["Open role questions still block handoff."],
                    "missing_evidence": ["No answered BA decision is cited."],
                    "recommendations": ["Resolve role questions before final Jira approval."],
                }
            ),
            model_name=self.model_name,
            provider_name=self.provider_name,
            token_usage={"prompt_tokens": 100, "completion_tokens": 40},
        )


def test_eval_profile_loader_reads_async_status_profile() -> None:
    profile = EvalProfileLoader().load("demo_team", "async-status-tracking")

    assert profile.profile_id == "async-status-tracking"
    assert "StatusTracker.java" in profile.expected_code
    assert "INC-103" in profile.expected_incidents


def test_evidence_coverage_analyzer_detects_memory_categories() -> None:
    markdown = """
# Engineering Brief

## Sources Used
- knowledge_packs/demo_team/docs/domain/execution-model.md
- knowledge_packs/demo_team/docs/architecture/status-tracking-design.md
- knowledge_packs/demo_team/docs/runbooks/status-stuck-running-runbook.md
- knowledge_packs/demo_team/docs/incidents/INC-103-status-stuck-running.md
- knowledge_packs/demo_team/docs/historical-jira/DFP-101-add-execution-status-tracking.md
- knowledge_packs/demo_team/docs/historical-pr/PR-502-add-execution-status-polling.md
- knowledge_packs/demo_team/docs/testing/status-transition-test-plan.md
- knowledge_packs/demo_team/docs/concepts/execution-status-memory.md
- backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
- backend-api/src/test/java/com/democorp/dfp/execution/StatusTrackerTest.java
"""

    coverage = EvidenceCoverageAnalyzer().analyze(markdown)

    assert all(coverage.values())


def test_evaluation_agent_scores_engineering_brief_artifact(tmp_path) -> None:
    artifact_dir = ensure_artifacts_dir() / "test-eval"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "strong-brief.md"
    artifact.write_text(
        """
# Engineering Brief

## 1. Request Summary
Add async status tracking so Analysts can see which Task is still RUNNING.

## 4. Impact Map
- workflow: execution status and task status transitions.
- frontend: execution-monitor.component.ts polling behavior.
- backend: StatusTracker.java, ExecutionService.java, ExecutionController.java.
- ops: status stuck RUNNING runbook and INC-103.
- test: StatusTrackerTest.java and ExecutionServiceTest.java regression coverage.

## 6. Role-specific Clarification Questions
## BA
- What status labels should users see?
## TL
- Should SERVICE_TASK and BATCH_TASK share the same status model?
## FE
- Should the Execution Monitor poll or subscribe to updates?
## BE
- What is the authoritative source for task status?
## QA
- What are the regression tests for stuck RUNNING state?
## OPS
- What runbook update is needed for stuck execution?

## 8. Test Strategy
- Add stuck RUNNING regression tests.
- Add task-level status transition tests.

## 11. Sources Used
- status-tracking-design.md
- execution-model.md
- job-lifecycle.md
- INC-103-status-stuck-running.md
- DFP-101-add-execution-status-tracking.md
- DFP-109-execution-monitor-auto-refresh.md
- PR-502-add-execution-status-polling.md
- PR-505-status-tracker-persistence.md
- StatusTracker.java
- ExecutionService.java
- ExecutionController.java
- BatchJobAdapter.java
- execution-monitor.component.ts
- StatusTrackerTest.java
- ExecutionServiceTest.java
""",
        encoding="utf-8",
    )
    repository = EvaluationRepository(tmp_path / "eval.sqlite")
    audit_repository = AuditRepository(tmp_path / "audit.sqlite")
    agent = EvaluationAgent(
        repository=repository,
        audit_repository=audit_repository,
        audit_logger=AuditLogger(repository=audit_repository),
    )

    result = agent.evaluate(
        EvaluationRequest(
            target_type="engineering_brief",
            artifact_path=display_path(artifact),
            team_id="demo_team",
            expected_profile="async-status-tracking",
        )
    )

    assert result.scorecard.overall_score >= 7.0
    assert result.scorecard.grade in {"A", "B"}
    assert repository.get(result.scorecard.evaluation_id) == result.scorecard


def test_evaluation_agent_can_attach_llm_judge_result(tmp_path) -> None:
    artifact_dir = ensure_artifacts_dir() / "test-eval"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "judge-brief.md"
    artifact.write_text(
        """
# Engineering Brief

## 1. Request Summary
Add async status tracking for running tasks.

## 4. Impact Map
- backend: StatusTracker.java
- frontend: execution-monitor.component.ts

## 6. Role-specific Clarification Questions
## BA
- What labels should users see?

## 8. Test Strategy
- Add StatusTrackerTest.java.

## 11. Sources Used
- status-tracking-design.md
- INC-103
- DFP-101
""",
        encoding="utf-8",
    )
    provider = FakeJudgeLLMProvider()
    repository = EvaluationRepository(tmp_path / "eval.sqlite")
    agent = EvaluationAgent(
        repository=repository,
        audit_repository=AuditRepository(tmp_path / "audit.sqlite"),
        llm_judge_provider=provider,
    )

    result = agent.evaluate(
        EvaluationRequest(
            target_type="engineering_brief",
            artifact_path=display_path(artifact),
            team_id="demo_team",
            judge_provider="fake-judge",
        )
    )

    assert provider.prompts
    assert result.scorecard.llm_judge is not None
    assert result.scorecard.llm_judge.status == "completed"
    assert result.scorecard.llm_judge.provider == "fake-judge"
    assert result.scorecard.llm_judge.model == "fake-judge-model"
    assert result.scorecard.llm_judge.readiness == "needs_review"
    assert result.scorecard.llm_judge.input_hash
    assert "## LLM Judge" in result.markdown_report
    assert repository.get(result.scorecard.evaluation_id) == result.scorecard


def test_evaluation_agent_flags_weak_pr_review(tmp_path) -> None:
    artifact_dir = ensure_artifacts_dir() / "test-eval"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "weak-pr-review.md"
    artifact.write_text(
        """
# AI PR Review Summary

## Overall Risk
Looks fine and approved.
""",
        encoding="utf-8",
    )
    agent = EvaluationAgent(
        repository=EvaluationRepository(tmp_path / "eval.sqlite"),
        audit_repository=AuditRepository(tmp_path / "audit.sqlite"),
    )

    result = agent.evaluate(
        EvaluationRequest(
            target_type="pr_review",
            artifact_path=display_path(artifact),
            team_id="demo_team",
        )
    )

    assert result.scorecard.pass_status in {"warning", "fail"}
    assert result.scorecard.hallucination_warnings


def test_eval_run_api_endpoint() -> None:
    artifact_dir = ensure_artifacts_dir() / "test-eval"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "api-brief.md"
    artifact.write_text(
        """
# Engineering Brief
## 1. Request Summary
StatusTracker.java needs async tracking.
## 4. Impact Map
- backend: StatusTracker.java
## 6. Role-specific Clarification Questions
## BA
- What status labels should users see?
## 8. Test Strategy
- Add StatusTrackerTest.java.
## 11. Sources Used
- INC-103
- DFP-101
- PR-502
- status-tracking-design.md
""",
        encoding="utf-8",
    )
    client = TestClient(create_app())

    response = client.post(
        "/eval/run",
        json={
            "target_type": "engineering_brief",
            "artifact_path": display_path(artifact),
            "team_id": "demo_team",
        },
    )

    assert response.status_code == 200
    assert response.json()["scorecard"]["target_type"] == "engineering_brief"
    evaluation_id = response.json()["scorecard"]["evaluation_id"]

    detail_response = client.get(f"/eval/runs/{evaluation_id}")

    assert detail_response.status_code == 200
    assert "# DREAM Evaluation Scorecard" in detail_response.json()["markdown_report"]
    assert detail_response.json()["json_path"].endswith(f"{evaluation_id}.json")
    assert detail_response.json()["markdown_path"].endswith(f"{evaluation_id}.md")
    assert "warnings" in detail_response.json()

    judge_response = client.post(
        f"/eval/runs/{evaluation_id}/judge",
        json={"judge_provider": "mock"},
    )

    assert judge_response.status_code == 200
    assert judge_response.json()["scorecard"]["llm_judge"]["status"] == "failed"
