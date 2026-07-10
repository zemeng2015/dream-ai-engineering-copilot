# SPDX-License-Identifier: Apache-2.0

from dream.evals.models import EvalProfile
from scripts.qwencloud_memory_ab_benchmark import (
    BENCHMARK_CASES,
    REQUIRED_SECTIONS,
    build_prompt,
    case_request,
    exact_paired_permutation_p,
    extract_references,
    score_output,
)


def _profile() -> EvalProfile:
    return EvalProfile(
        profile_id="fixture",
        title="Fixture",
        expected_concepts=["execution status", "polling"],
        expected_code=["StatusTracker.java"],
        expected_tests=["StatusTrackerTest.java"],
        expected_docs=["status-tracking-design.md"],
        expected_incidents=["INC-103"],
        expected_jira=["DFP-101"],
        expected_pr=["PR-502"],
        expected_roles=["BA", "TL", "FE", "BE", "QA", "OPS"],
        critical_risks=["status stuck RUNNING"],
    )


def test_benchmark_uses_all_preexisting_golden_profiles() -> None:
    assert [case["profile_id"] for case in BENCHMARK_CASES] == [
        "async-status-tracking",
        "output-collection-idempotency",
        "task-config-validation",
        "partial-execution-recovery",
        "workflow-versioning",
        "operator-retry-action",
        "large-output-preview",
    ]
    assert case_request(BENCHMARK_CASES[0]).startswith("Users want to know which task")


def test_stateless_prompt_does_not_leak_expected_source_names() -> None:
    prompt = build_prompt("Add live job progress.", None)

    assert "No organization-specific evidence was provided." in prompt
    assert "StatusTracker.java" not in prompt
    assert "INC-103" not in prompt
    assert all(f"## {section}" in prompt for section in REQUIRED_SECTIONS)


def test_deterministic_score_rewards_expected_evidence_and_penalizes_invention() -> None:
    profile = _profile()
    headings = "\n".join(f"## {section}" for section in REQUIRED_SECTIONS)
    output = f"""{headings}
execution status polling status stuck RUNNING
StatusTracker.java StatusTrackerTest.java status-tracking-design.md
INC-103 DFP-101 PR-502 ImaginaryController.java
BA TL FE BE QA OPS
"""
    references = {
        "statustracker.java",
        "statustrackertest.java",
        "status-tracking-design.md",
        "inc-103",
        "dfp-101",
        "pr-502",
    }

    metrics = score_output(output, profile, references, references)

    assert metrics["domain_recall"] == 1.0
    assert metrics["expected_source_recall"] == 1.0
    assert metrics["role_coverage"] == 1.0
    assert metrics["section_coverage"] == 1.0
    assert metrics["valid_reference_count"] == 6
    assert metrics["unsupported_references"] == ["imaginarycontroller.java"]
    assert metrics["unsupported_penalty"] == 4.0
    assert metrics["grounding_score"] == 96.0


def test_reference_extraction_is_case_insensitive_and_deduplicated() -> None:
    assert extract_references(
        "INC-103 and inc-103 use StatusTracker.java with status-tracking-design.md"
    ) == ["inc-103", "status-tracking-design.md", "statustracker.java"]


def test_unseen_real_reference_is_not_credited_as_grounded() -> None:
    metrics = score_output(
        "INC-103 StatusTracker.java",
        _profile(),
        {"statustracker.java"},
        {"inc-103", "statustracker.java"},
    )

    assert metrics["valid_references"] == ["statustracker.java"]
    assert metrics["unseen_known_references"] == ["inc-103"]
    assert metrics["unsupported_reference_count"] == 1


def test_exact_paired_permutation_is_deterministic() -> None:
    assert exact_paired_permutation_p([10.0, 10.0, 10.0]) == 0.25
    assert exact_paired_permutation_p([0.0, 0.0]) == 1.0
