# SPDX-License-Identifier: Apache-2.0

import json

from scripts.qwencloud_experience_memory_benchmark import (
    DEFAULT_CASES,
    _semantic_token_overlap,
    load_cases,
    rescore_report,
    run_benchmark,
    write_reports,
)


def _cases() -> list[dict[str, object]]:
    return [
        {
            "id": "preference-carryover",
            "category": "preference",
            "steps": [
                {
                    "day_offset": 0,
                    "natural_observation": "Prefer failed-only production retries.",
                    "expected": {
                        "action": "remember",
                        "kind": "preference",
                        "key": "production_retry_mode",
                        "value": "retry only failed tasks",
                        "importance": 5,
                    },
                }
            ],
            "recall": {
                "day_offset": 1,
                "query": "production retry mode",
                "token_budget": 128,
                "expected_keys": ["production_retry_mode"],
                "forbidden_values": [],
            },
        },
        {
            "id": "preference-supersession",
            "category": "conflict",
            "steps": [
                {
                    "day_offset": 0,
                    "natural_observation": "Retry every task.",
                    "expected": {
                        "action": "remember",
                        "kind": "preference",
                        "key": "production_retry_mode",
                        "value": "retry all tasks",
                    },
                },
                {
                    "day_offset": 1,
                    "natural_observation": "Use failed-only retries instead.",
                    "expected": {
                        "proposal_action": "remember",
                        "actual_action": "supersede",
                        "kind": "preference",
                        "key": "production_retry_mode",
                        "value": "retry only failed tasks",
                    },
                },
            ],
            "recall": {
                "day_offset": 2,
                "query": "production retry mode",
                "token_budget": 128,
                "expected_keys": ["production_retry_mode"],
                "forbidden_values": ["retry all tasks"],
            },
        },
    ]


def test_deterministic_experience_benchmark_scores_full_lifecycle() -> None:
    report = run_benchmark(_cases(), policy_mode="deterministic")

    assert report["case_count"] == 2
    assert report["aggregate"]["passed_cases"] == 2
    assert report["aggregate"]["proposal_accuracy"] == 1.0
    assert report["aggregate"]["action_accuracy"] == 1.0
    assert report["aggregate"]["critical_memory_recall"] == 1.0
    assert report["aggregate"]["forbidden_memory_leak_rate"] == 0.0
    assert report["aggregate"]["overall_score"] == 100.0


def test_experience_benchmark_writes_public_json_and_markdown(tmp_path) -> None:
    report = run_benchmark(_cases(), policy_mode="deterministic")
    json_path, markdown_path = write_reports(report, tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert payload["schema_version"] == "experience-benchmark-v1"
    assert payload["aggregate"]["stateless_baseline_carryover_recall"] == 0.0
    assert "DREAM Track 1 Experience Memory Benchmark" in markdown
    assert "preference-supersession" in markdown


def test_experience_benchmark_yaml_requires_unique_case_ids(tmp_path) -> None:
    path = tmp_path / "cases.yaml"
    path.write_text(
        """cases:
  - id: duplicate
    steps: []
    recall: {}
  - id: duplicate
    steps: []
    recall: {}
""",
        encoding="utf-8",
    )

    try:
        load_cases(path)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("Duplicate benchmark ids should be rejected.")


def test_default_experience_scenarios_cover_track_one_lifecycle() -> None:
    cases = load_cases(DEFAULT_CASES)
    categories = [case["category"] for case in cases]

    assert len(cases) == 24
    assert len({case["id"] for case in cases}) == 24
    assert categories.count("cross_session_preference") == 8
    assert categories.count("conflict_supersede") == 6
    assert categories.count("ttl_or_forget") == 4
    assert categories.count("limited_token_budget") == 4
    assert categories.count("duplicate_or_ignore") == 2


def test_semantic_payload_scores_gold_concept_coverage() -> None:
    assert _semantic_token_overlap(
        "Do not publish a release artifact unless provenance is signed and verified.",
        "require signed and verified provenance",
    ) >= 0.5
    assert _semantic_token_overlap(
        "signed artifact",
        "require signed and verified provenance",
    ) < 0.5


def test_rescore_keeps_payload_drift_diagnostic_not_lifecycle_blocking() -> None:
    report = run_benchmark(_cases(), policy_mode="deterministic")
    report["cases"][0]["steps"][0]["memory_ok"] = False
    report["cases"][0]["passed"] = False

    rescored = rescore_report(report)

    assert rescored["cases"][0]["passed"] is True
    assert rescored["cases"][0]["payload_diagnostic_pass"] is False
    assert rescored["aggregate"]["memory_payload_accuracy"] < 1.0
    assert rescored["aggregate"]["passed_cases"] == 2
