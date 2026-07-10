# SPDX-License-Identifier: Apache-2.0

from dream.leadership_demo.rehearsal import LeadershipRehearsalRunner
from dream.leadership_demo.service import LeadershipDemoService


def test_rehearsal_closes_human_gate_and_restores_blocked_baseline(tmp_path) -> None:
    service = LeadershipDemoService(
        artifacts_dir=tmp_path / "artifacts",
        db_path=tmp_path / "leadership.sqlite",
    )
    report = LeadershipRehearsalRunner(service=service).run(
        output_dir=tmp_path / "rehearsal"
    )

    assert report.passed
    assert not report.before_jira_ready
    assert len(report.before_open_question_ids) == 1
    assert report.after_jira_ready
    assert report.after_open_question_ids == []
    assert report.claim_proof_preserved
    assert report.case_audit_records_after > report.case_audit_records_before
    assert report.external_writes_performed is False
    assert report.baseline_restored
    assert not report.restored_jira_ready
    assert len(report.restored_open_question_ids) == 1

    restored = service.requirement_repository.get(report.case_id)
    assert restored.jira_readiness is not None
    assert not restored.jira_readiness.ready
    assert len([item for item in restored.questions if item.status == "open"]) == 1
    assert (tmp_path / "rehearsal/leadership-rehearsal.json").exists()
    assert (tmp_path / "rehearsal/leadership-rehearsal.md").exists()
