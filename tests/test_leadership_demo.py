# SPDX-License-Identifier: Apache-2.0

import pytest

from dream.context.repository import ContextArtifactRepository
from dream.core.errors import DreamError
from dream.leadership_demo import (
    LEADERSHIP_DEMO_CASE_ID,
    LEADERSHIP_DEMO_REPO_NAME,
    LEADERSHIP_DEMO_SCAN_ID,
    LeadershipDemoService,
)


def test_leadership_demo_seed_is_replayable_and_dfp_only(monkeypatch, tmp_path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    db_path = tmp_path / "dream.sqlite"
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(artifacts_dir))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(db_path))
    service = LeadershipDemoService(artifacts_dir=artifacts_dir, db_path=db_path)

    first = service.seed(reset=True)
    first_snapshot = service.requirement_repository.get(LEADERSHIP_DEMO_CASE_ID)
    first_case_audit_count = len(
        [
            record
            for record in service.audit_repository.list_audit_records()
            if record.case_id == LEADERSHIP_DEMO_CASE_ID
        ]
    )
    first_trail = ContextArtifactRepository().load_trail(first.context_trail_id)

    assert first.case_id == LEADERSHIP_DEMO_CASE_ID
    assert first.repo_name == LEADERSHIP_DEMO_REPO_NAME
    assert first.scan_id == LEADERSHIP_DEMO_SCAN_ID
    assert first.jira_ready is False
    assert len(first.open_question_ids) == 1
    assert first.evidence_count == len(first_snapshot.evidence)
    assert first_snapshot.jira_draft is not None
    assert first_snapshot.jira_readiness is not None
    assert first_snapshot.jira_readiness.open_questions == 1
    assert any(
        item.memory_claim_id == first.approved_claim_id
        and item.governance_status == "approved"
        and item.reviewed_by == "DREAM Leadership Demo Reviewer"
        for item in first_snapshot.evidence
    )
    assert any(
        claim.claim_id == first.approved_claim_id for claim in first_trail.memory_claims_used
    )
    assert all("java-demo-repo" not in path for path in first.source_paths)
    assert any(
        "backend-api/src/main/java/com/democorp/dfp/execution/" in path
        for path in first.source_paths
    )
    assert any("frontend/src/app/execution/" in path for path in first.source_paths)
    expected_code = {
        "StatusTracker.java",
        "ExecutionService.java",
        "ExecutionController.java",
        "BatchJobAdapter.java",
        "execution-monitor.component.ts",
    }
    expected_tests = {
        "StatusTrackerTest.java",
        "ExecutionServiceTest.java",
    }
    expected_history = {"INC-103", "DFP-101", "DFP-109", "PR-502", "PR-505"}
    source_text = "\n".join(first.source_paths)
    assert all(item in source_text for item in expected_code)
    assert all(item in source_text for item in expected_tests)
    assert all(item in source_text for item in expected_history)
    assert (
        service.codebase_repository.load("demo_team", LEADERSHIP_DEMO_REPO_NAME).repo_name
        == LEADERSHIP_DEMO_REPO_NAME
    )
    assert (
        service.memory_repository.load_scan("demo_team", LEADERSHIP_DEMO_SCAN_ID).repo_name
        == LEADERSHIP_DEMO_REPO_NAME
    )
    assert service.evaluation_repository.get(first.evaluation_id) is not None

    with pytest.raises(DreamError, match="already exists"):
        service.seed()

    second = service.seed(reset=True)
    second_case_audit_count = len(
        [
            record
            for record in service.audit_repository.list_audit_records()
            if record.case_id == LEADERSHIP_DEMO_CASE_ID
        ]
    )
    claim_review_events = [
        event
        for event in service.memory_repository.load_ledger("demo_team").events
        if event.claim_id == first.approved_claim_id
    ]

    assert second.case_id == first.case_id
    assert second.scan_id == first.scan_id
    assert second.approved_claim_id == first.approved_claim_id
    assert second.context_trail_id == first.context_trail_id
    assert second.source_paths == first.source_paths
    assert second_case_audit_count == first_case_audit_count
    assert len(claim_review_events) == 1
    assert (
        len(
            [
                scorecard
                for scorecard in service.evaluation_repository.list()
                if scorecard.case_id == LEADERSHIP_DEMO_CASE_ID
            ]
        )
        == 1
    )
