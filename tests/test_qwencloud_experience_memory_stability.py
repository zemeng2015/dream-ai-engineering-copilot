# SPDX-License-Identifier: Apache-2.0

import json

from scripts.qwencloud_experience_memory_stability import (
    run_stability,
    write_stability_report,
)
from tests.test_qwencloud_experience_memory_benchmark import _cases


def test_deterministic_stability_requires_repeatable_lifecycle_results(tmp_path) -> None:
    report = run_stability(_cases(), runs=2, policy_mode="deterministic")

    aggregate = report["aggregate"]
    assert aggregate["all_runs_passed"] is True
    assert aggregate["passed_run_count"] == 2
    assert aggregate["consistently_passed_cases"] == 2
    assert aggregate["step_action_agreement"] == 1.0
    assert aggregate["qwen_receipt_coverage"] == 1.0

    json_path, markdown_path = write_stability_report(report, tmp_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["run_count"] == 2
    assert "Step action agreement" in markdown_path.read_text(encoding="utf-8")
