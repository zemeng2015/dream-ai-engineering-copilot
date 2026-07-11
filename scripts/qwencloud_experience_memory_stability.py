# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.qwencloud_experience_memory_benchmark import (  # noqa: E402
    DEFAULT_CASES,
    DEFAULT_OUTPUT_DIR,
    load_cases,
    load_env_file,
    run_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repeat the DREAM Qwen experience benchmark and measure stability."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.qwencloud.local")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--attempts", type=int, default=3)
    return parser.parse_args()


def run_stability(
    cases: list[dict[str, Any]],
    *,
    runs: int,
    attempts: int = 3,
    policy_mode: str = "qwen-cloud",
) -> dict[str, Any]:
    if runs < 2:
        raise ValueError("Stability measurement requires at least two runs.")
    started_at = datetime.now(UTC)
    reports = [
        run_benchmark(cases, policy_mode=policy_mode, attempts=attempts)
        for _ in range(runs)
    ]
    case_ids = [str(case["id"]) for case in cases]
    cases_by_run = [
        {str(case["id"]): case for case in report["cases"]} for report in reports
    ]
    consistently_passed = sum(
        all(run_cases[case_id]["passed"] for run_cases in cases_by_run)
        for case_id in case_ids
    )
    action_checks = 0
    action_agreements = 0
    for case_id in case_ids:
        step_count = len(cases_by_run[0][case_id]["steps"])
        for step_index in range(step_count):
            signatures = {
                (
                    run_cases[case_id]["steps"][step_index]["actual_proposal"],
                    run_cases[case_id]["steps"][step_index]["actual_action"],
                )
                for run_cases in cases_by_run
            }
            action_checks += 1
            action_agreements += len(signatures) == 1

    total_decisions = sum(
        report["aggregate"]["qwen_decision_count"] for report in reports
    )
    total_receipts = sum(
        report["aggregate"]["qwen_receipt_count"] for report in reports
    )
    total_tokens = sum(report["aggregate"]["qwen_total_tokens"] for report in reports)
    all_runs_passed = all(
        report["aggregate"]["passed_cases"] == report["case_count"]
        for report in reports
    )
    finished_at = datetime.now(UTC)
    return {
        "schema_version": "experience-stability-v1",
        "run_id": started_at.strftime("%Y%m%dT%H%M%SZ"),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "policy_mode": policy_mode,
        "provider": reports[0]["provider"],
        "model": reports[0]["model"],
        "run_count": runs,
        "case_count": len(cases),
        "aggregate": {
            "all_runs_passed": all_runs_passed,
            "passed_run_count": sum(
                report["aggregate"]["passed_cases"] == report["case_count"]
                for report in reports
            ),
            "consistently_passed_cases": consistently_passed,
            "case_pass_stability": round(consistently_passed / len(cases), 4),
            "step_action_agreement": round(
                action_agreements / max(1, action_checks), 4
            ),
            "qwen_receipt_coverage": round(
                total_receipts / total_decisions if total_decisions else 1.0, 4
            ),
            "qwen_decision_count": total_decisions,
            "qwen_receipt_count": total_receipts,
            "qwen_total_tokens": total_tokens,
        },
        "runs": reports,
        "limitations": [
            "Repeated synthetic scenarios measure consistency, not production impact.",
            "Temperature zero reduces but does not eliminate provider-side variation.",
        ],
    }


def write_stability_report(
    report: dict[str, Any], output_dir: Path
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"experience-memory-stability-{report['run_id']}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    aggregate = report["aggregate"]
    lines = [
        "# DREAM Qwen Experience Memory Stability",
        "",
        f"- Run: `{report['run_id']}`",
        f"- Provider/model: `{report['provider']}` / `{report['model']}`",
        f"- Repetitions: {report['run_count']}",
        f"- All runs passed: {'yes' if aggregate['all_runs_passed'] else 'no'}",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Passed runs | {aggregate['passed_run_count']}/{report['run_count']} |",
        "| Consistently passed cases | "
        f"{aggregate['consistently_passed_cases']}/{report['case_count']} |",
        f"| Step action agreement | {aggregate['step_action_agreement']:.1%} |",
        f"| Qwen receipt coverage | {aggregate['qwen_receipt_coverage']:.1%} |",
        f"| Qwen decisions | {aggregate['qwen_decision_count']} |",
        f"| Qwen tokens | {aggregate['qwen_total_tokens']:,} |",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in report["limitations"])
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    args = parse_args()
    load_env_file(args.env_file)
    report = run_stability(
        load_cases(args.cases), runs=args.runs, attempts=args.attempts
    )
    json_path, markdown_path = write_stability_report(report, args.output_dir)
    print(f"Stability JSON: {json_path}")
    print(f"Stability Markdown: {markdown_path}")
    aggregate = report["aggregate"]
    passed = (
        aggregate["all_runs_passed"]
        and aggregate["step_action_agreement"] == 1.0
        and aggregate["qwen_receipt_coverage"] == 1.0
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
