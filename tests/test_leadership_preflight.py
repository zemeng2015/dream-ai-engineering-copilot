# SPDX-License-Identifier: Apache-2.0

from dream.leadership_demo.preflight import LeadershipPreflightRunner
from dream.leadership_demo.service import LeadershipDemoService


def test_preflight_proves_demo_contract_and_reports_non_blocking_evidence_gaps(
    tmp_path,
) -> None:
    service = LeadershipDemoService(
        artifacts_dir=tmp_path / "artifacts",
        db_path=tmp_path / "leadership.sqlite",
    )
    report = LeadershipPreflightRunner(service=service).run(
        output_dir=tmp_path / "preflight",
        repetitions=3,
        branch_name="codex/leadership-product",
        working_tree_dirty=False,
    )

    assert report.ready_for_demo
    status_by_id = {item.check_id: item.status for item in report.checks}
    assert status_by_id["product_branch"] == "pass"
    assert status_by_id["fixed_scenario"] == "pass"
    assert status_by_id["approved_claim_consumed"] == "pass"
    assert status_by_id["human_gate"] == "pass"
    assert status_by_id["synthetic_source_boundary"] == "pass"
    assert status_by_id["provider_profile_isolation"] == "pass"
    assert status_by_id["paired_benchmark_harness"] == "pass"
    assert any("approved" in item and "SME" in item for item in report.next_actions)
    assert (tmp_path / "preflight/leadership-preflight.json").exists()
    assert (tmp_path / "preflight/leadership-preflight.md").exists()


def test_preflight_rejects_competition_branch_and_strict_dirty_tree(tmp_path) -> None:
    service = LeadershipDemoService(
        artifacts_dir=tmp_path / "artifacts",
        db_path=tmp_path / "leadership.sqlite",
    )
    report = LeadershipPreflightRunner(service=service).run(
        output_dir=tmp_path / "preflight",
        repetitions=3,
        strict_git=True,
        branch_name="codex/champion-memory-loop",
        working_tree_dirty=True,
    )

    assert not report.ready_for_demo
    assert any(item.check_id == "product_branch" for item in report.checks if item.status == "fail")
    assert any(item.check_id == "git_hygiene" for item in report.checks if item.status == "fail")
