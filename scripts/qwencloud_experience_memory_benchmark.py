# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dream.core.errors import DreamError, ProviderRequestError  # noqa: E402
from dream.experience import (  # noqa: E402
    ExperienceMemoryRepository,
    ExperienceMemoryService,
    ExperienceObservation,
    ExperiencePolicyResult,
    ExperienceRecallRequest,
    LLMExperienceMemoryPolicy,
    MemoryActionProposal,
)
from dream.llm.qwen_cloud import QwenCloudProvider  # noqa: E402

DEFAULT_CASES = ROOT / "examples" / "experience-benchmark" / "scenarios.yaml"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "qwencloud-experience-benchmarks"
ALLOWED_ENV_KEYS = {
    "DASHSCOPE_API_KEY",
    "QWEN_API_KEY",
    "QWEN_BASE_URL",
    "DASHSCOPE_BASE_URL",
    "QWEN_MODEL",
    "QWEN_TIMEOUT_SECONDS",
    "QWEN_MAX_COMPLETION_TOKENS",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run DREAM's cross-session Track 1 experience-memory benchmark."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--policy",
        choices=("deterministic", "qwen-cloud"),
        default="deterministic",
    )
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.qwencloud.local")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument(
        "--rescore",
        type=Path,
        help="Recompute lifecycle pass/fail and aggregate metrics from an existing report.",
    )
    return parser.parse_args()


def load_env_file(path: Path) -> list[str]:
    if not path.is_file():
        return []
    loaded: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if name not in ALLOWED_ENV_KEYS or os.getenv(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            os.environ[name] = value
            loaded.append(name)
    return loaded


def load_cases(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Benchmark YAML must contain a mapping.")
    cases = payload.get("cases") or payload.get("scenarios")
    if not isinstance(cases, list):
        raise ValueError("Benchmark YAML must contain a top-level cases or scenarios list.")
    if not cases:
        raise ValueError("Benchmark cases list is empty.")
    identifiers = [str(case.get("id", "")) for case in cases]
    if any(not value for value in identifiers) or len(identifiers) != len(set(identifiers)):
        raise ValueError("Every benchmark case requires a unique non-empty id.")
    return cases


def run_benchmark(
    cases: list[dict[str, Any]],
    *,
    policy_mode: str,
    attempts: int = 3,
) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    provider = QwenCloudProvider() if policy_mode == "qwen-cloud" else None
    case_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="dream-experience-benchmark-") as temp_dir:
        root = Path(temp_dir)
        for index, case in enumerate(cases, start=1):
            case_results.append(
                run_case(
                    case,
                    db_path=root / f"case-{index:02d}.sqlite",
                    policy_mode=policy_mode,
                    provider=provider,
                    attempts=attempts,
                )
            )

    aggregate = aggregate_results(case_results)
    finished_at = datetime.now(UTC)
    return {
        "schema_version": "experience-benchmark-v1",
        "run_id": started_at.strftime("%Y%m%dT%H%M%SZ"),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "policy_mode": policy_mode,
        "provider": provider.provider_name if provider else "deterministic-proposal",
        "model": provider.model_name if provider else "experience-lifecycle-v1",
        "case_count": len(case_results),
        "aggregate": aggregate,
        "cases": case_results,
        "limitations": [
            "Synthetic engineering scenarios do not establish production effectiveness.",
            (
                "The deterministic mode validates lifecycle mechanics, not "
                "natural-language extraction."
            ),
            "The qwen-cloud mode uses one curator decision per benchmark step.",
            "A stateless baseline has no cross-session memory and therefore zero carryover recall.",
        ],
    }


def run_case(
    case: dict[str, Any],
    *,
    db_path: Path,
    policy_mode: str,
    provider: QwenCloudProvider | None,
    attempts: int,
) -> dict[str, Any]:
    repository = ExperienceMemoryRepository(db_path)
    qwen_policy = LLMExperienceMemoryPolicy(provider) if provider else None
    service = ExperienceMemoryService(repository=repository, policy=qwen_policy)
    baseline = datetime(2026, 1, 1, tzinfo=UTC)
    team_id = str(case.get("team_id") or "demo_team")
    user_id = str(case.get("user_id") or f"benchmark-{case['id']}")
    step_results: list[dict[str, Any]] = []
    expected_memory_ids: dict[str, str] = {}

    for index, step in enumerate(case.get("steps") or [], start=1):
        expected = _expected(step)
        observation = ExperienceObservation(
            team_id=team_id,
            user_id=user_id,
            session_id=str(step.get("session_id") or f"session-{index}"),
            observation=str(step["natural_observation"]),
            source_reference=f"benchmark:{case['id']}:step-{index}",
        )
        now = baseline + timedelta(days=float(step.get("day_offset", index - 1)))
        try:
            if policy_mode == "qwen-cloud":
                capture = _capture_with_retry(service, observation, now, attempts)
            else:
                proposal = _proposal_from_expected(expected, repository, team_id, user_id)
                capture = service.apply_policy_result(
                    observation,
                    ExperiencePolicyResult(
                        proposal=proposal,
                        provider_name="deterministic-proposal",
                        model_name="experience-lifecycle-v1",
                    ),
                    now=now,
                )
        except DreamError as exc:
            step_results.append(
                {
                    "step": index,
                    "session_id": observation.session_id,
                    "expected_proposal": _expected_proposal_action(expected),
                    "actual_proposal": "error",
                    "proposal_ok": False,
                    "expected_action": _expected_actual_action(expected),
                    "actual_action": "error",
                    "requested_action": "error",
                    "action_ok": False,
                    "memory_ok": False,
                    "exact_key_ok": False,
                    "created_memory_id": None,
                    "target_memory_id": None,
                    "provider": provider.provider_name if provider else "deterministic-proposal",
                    "model": provider.model_name if provider else "experience-lifecycle-v1",
                    "token_usage": None,
                    "actual_memory": None,
                    "error": str(exc),
                }
            )
            continue
        actual_memory = capture.memory
        expected_proposal = _expected_proposal_action(expected)
        proposal_ok = capture.decision.requested_action == expected_proposal
        action_ok = capture.decision.action == _expected_actual_action(expected)
        memory_ok = _memory_matches(actual_memory, expected)
        exact_key_ok = _exact_key_matches(actual_memory, expected)
        if actual_memory is not None and expected.get("key"):
            expected_memory_ids[str(expected["key"])] = actual_memory.memory_id
        step_results.append(
            {
                "step": index,
                "session_id": observation.session_id,
                "expected_proposal": expected_proposal,
                "actual_proposal": capture.decision.requested_action,
                "proposal_ok": proposal_ok,
                "expected_action": _expected_actual_action(expected),
                "actual_action": capture.decision.action,
                "requested_action": capture.decision.requested_action,
                "action_ok": action_ok,
                "memory_ok": memory_ok,
                "exact_key_ok": exact_key_ok,
                "created_memory_id": capture.decision.created_memory_id,
                "target_memory_id": capture.decision.target_memory_id,
                "provider": capture.decision.provider_name,
                "model": capture.decision.model_name,
                "token_usage": capture.decision.token_usage,
                "actual_memory": (
                    {
                        "memory_id": actual_memory.memory_id,
                        "kind": actual_memory.kind,
                        "key": actual_memory.key,
                        "value": actual_memory.value,
                        "importance": actual_memory.importance,
                        "valid_until": actual_memory.valid_until,
                    }
                    if actual_memory
                    else None
                ),
            }
        )

    recall_spec = case.get("recall") or {}
    recall = service.recall(
        ExperienceRecallRequest(
            team_id=team_id,
            user_id=user_id,
            session_id=str(recall_spec.get("session_id") or "recall-session"),
            query=str(recall_spec.get("query") or "relevant memory"),
            token_budget=int(recall_spec.get("token_budget") or 512),
            limit=int(recall_spec.get("limit") or 12),
        ),
        now=baseline + timedelta(days=float(recall_spec.get("day_offset", 30))),
    )
    selected_keys = [item.memory.key for item in recall.selected]
    selected_values = [item.memory.value for item in recall.selected]
    selected_memory_ids = [item.memory.memory_id for item in recall.selected]
    expected_keys = [str(value) for value in recall_spec.get("expected_keys") or []]
    forbidden_values = [str(value) for value in recall_spec.get("forbidden_values") or []]
    expected_ids = [expected_memory_ids.get(key) for key in expected_keys]
    expected_hits = sum(
        memory_id is not None and memory_id in selected_memory_ids
        for memory_id in expected_ids
    )
    leaked_values = [
        value
        for value in forbidden_values
        if any(
            _normalized_text(value) == _normalized_text(selected)
            for selected in selected_values
        )
    ]
    recall_score = expected_hits / len(expected_keys) if expected_keys else 1.0
    steps_pass = all(item["proposal_ok"] and item["action_ok"] for item in step_results)
    payload_diagnostic_pass = all(item["memory_ok"] for item in step_results)
    budget_ok = recall.estimated_tokens_used <= recall.token_budget
    case_pass = steps_pass and recall_score == 1.0 and not leaked_values and budget_ok
    return {
        "id": str(case["id"]),
        "category": str(case.get("category") or "uncategorized"),
        "passed": case_pass,
        "payload_diagnostic_pass": payload_diagnostic_pass,
        "steps": step_results,
        "recall": {
            "expected_keys": expected_keys,
            "expected_memory_ids": expected_ids,
            "selected_keys": selected_keys,
            "selected_values": selected_values,
            "selected_memory_ids": selected_memory_ids,
            "expected_hits": expected_hits,
            "expected_total": len(expected_keys),
            "recall": round(recall_score, 4),
            "forbidden_values": forbidden_values,
            "leaked_values": leaked_values,
            "expired_memory_ids": recall.expired_memory_ids,
            "token_budget": recall.token_budget,
            "estimated_tokens_used": recall.estimated_tokens_used,
            "budget_ok": budget_ok,
        },
    }


def _capture_with_retry(
    service: ExperienceMemoryService,
    observation: ExperienceObservation,
    now: datetime,
    attempts: int,
):
    last_error: Exception | None = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return service.capture(observation, now=now)
        except (ProviderRequestError, DreamError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
    assert last_error is not None
    raise last_error


def _expected(step: dict[str, Any]) -> dict[str, Any]:
    value = step.get("expected")
    if isinstance(value, dict):
        return value
    if not step.get("expected_action") and not step.get("expected_proposal"):
        raise ValueError("Every benchmark step requires expected action fields.")
    return {
        "proposal_action": step.get("expected_proposal"),
        "actual_action": step.get("expected_action"),
        "kind": step.get("kind"),
        "key": step.get("key"),
        "value": step.get("value"),
        "importance": step.get("importance"),
        "ttl_days": step.get("ttl_days"),
        "target_key": step.get("target_key"),
    }


def _expected_actual_action(expected: dict[str, Any]) -> str:
    return str(expected.get("actual_action") or expected.get("action") or "remember")


def _expected_proposal_action(expected: dict[str, Any]) -> str:
    return str(
        expected.get("proposal_action") or expected.get("action") or "remember"
    )


def _proposal_from_expected(
    expected: dict[str, Any],
    repository: ExperienceMemoryRepository,
    team_id: str,
    user_id: str,
) -> MemoryActionProposal:
    proposal_action = _expected_proposal_action(expected)
    target_memory_id = expected.get("target_memory_id")
    target_key = expected.get("target_key")
    if target_key and not target_memory_id:
        target = next(
            (
                memory
                for memory in repository.list_memories(
                    team_id=team_id,
                    user_id=user_id,
                    include_inactive=False,
                )
                if memory.key == str(target_key)
            ),
            None,
        )
        target_memory_id = target.memory_id if target else None
    return MemoryActionProposal(
        action=proposal_action,
        kind=expected.get("kind"),
        key=expected.get("key"),
        value=expected.get("value"),
        target_memory_id=target_memory_id,
        confidence=float(expected.get("confidence") or 0.9),
        importance=int(expected.get("importance") or 3),
        ttl_days=expected.get("ttl_days"),
        rationale=str(expected.get("rationale") or "Benchmark expected action."),
    )


def _memory_matches(memory, expected: dict[str, Any]) -> bool:
    action = _expected_actual_action(expected)
    if action in {"forget", "ignore"}:
        return memory is None
    if memory is None:
        return False
    kind_ok = expected.get("kind") is None or memory.kind == expected["kind"]
    if expected.get("value") is None:
        value_ok = True
    else:
        value_ok = _semantic_token_overlap(memory.value, str(expected["value"])) >= 0.5
    return kind_ok and value_ok


def _exact_key_matches(memory, expected: dict[str, Any]) -> bool:
    action = _expected_actual_action(expected)
    if action in {"forget", "ignore"}:
        return memory is None
    if memory is None or expected.get("key") is None:
        return False
    return memory.key == str(expected["key"])


def _normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def _semantic_token_overlap(left: str, right: str) -> float:
    aliases = {
        "alerting": "alert",
        "alerts": "alert",
        "days": "day",
        "minutes": "minute",
        "nonprod": "nonproduction",
        "notification": "notify",
        "notifications": "notify",
        "notified": "notify",
        "paging": "page",
        "percentage": "percent",
        "rerun": "retry",
        "tasks": "task",
        "workers": "worker",
    }
    left_tokens = {
        aliases.get(token, token) for token in re.findall(r"[a-z0-9]+", left.lower())
    }
    right_tokens = {
        aliases.get(token, token) for token in re.findall(r"[a-z0-9]+", right.lower())
    }
    if not right_tokens:
        return 1.0
    intersection = len(left_tokens & right_tokens)
    return intersection / len(right_tokens)


def aggregate_results(cases: list[dict[str, Any]]) -> dict[str, Any]:
    steps = [step for case in cases for step in case["steps"]]
    expected_total = sum(case["recall"]["expected_total"] for case in cases)
    expected_hits = sum(case["recall"]["expected_hits"] for case in cases)
    forbidden_total = sum(len(case["recall"]["forbidden_values"]) for case in cases)
    leaked_total = sum(len(case["recall"]["leaked_values"]) for case in cases)
    proposal_accuracy = sum(step["proposal_ok"] for step in steps) / max(1, len(steps))
    action_accuracy = sum(step["action_ok"] for step in steps) / max(1, len(steps))
    memory_accuracy = sum(step["memory_ok"] for step in steps) / max(1, len(steps))
    exact_key_accuracy = sum(step["exact_key_ok"] for step in steps) / max(1, len(steps))
    recall = expected_hits / expected_total if expected_total else 1.0
    leak_rate = leaked_total / forbidden_total if forbidden_total else 0.0
    budget_compliance = sum(case["recall"]["budget_ok"] for case in cases) / len(cases)
    categories = sorted({case["category"] for case in cases})
    category_pass_rates = {
        category: round(
            sum(case["passed"] for case in cases if case["category"] == category)
            / sum(case["category"] == category for case in cases),
            4,
        )
        for category in categories
    }
    overall = 100 * (
        0.15 * proposal_accuracy
        + 0.15 * action_accuracy
        + 0.10 * memory_accuracy
        + 0.35 * recall
        + 0.15 * (1.0 - leak_rate)
        + 0.10 * budget_compliance
    )
    return {
        "passed_cases": sum(case["passed"] for case in cases),
        "proposal_accuracy": round(proposal_accuracy, 4),
        "action_accuracy": round(action_accuracy, 4),
        "memory_payload_accuracy": round(memory_accuracy, 4),
        "exact_canonical_key_accuracy": round(exact_key_accuracy, 4),
        "critical_memory_recall": round(recall, 4),
        "forbidden_memory_leak_rate": round(leak_rate, 4),
        "token_budget_compliance": round(budget_compliance, 4),
        "stateless_baseline_carryover_recall": 0.0,
        "overall_score": round(overall, 1),
        "category_pass_rates": category_pass_rates,
    }


def rescore_report(report: dict[str, Any]) -> dict[str, Any]:
    rescored = json.loads(json.dumps(report))
    for case in rescored["cases"]:
        recall = case["recall"]
        case["payload_diagnostic_pass"] = all(
            step["memory_ok"] for step in case["steps"]
        )
        case["passed"] = (
            all(step["proposal_ok"] and step["action_ok"] for step in case["steps"])
            and recall["recall"] == 1.0
            and not recall["leaked_values"]
            and recall["budget_ok"]
        )
    rescored["aggregate"] = aggregate_results(rescored["cases"])
    rescored["scoring_revision"] = "experience-lifecycle-score-v1.1"
    rescored["rescored_at"] = datetime.now(UTC).isoformat()
    rescored["run_id"] = f"{report['run_id']}-R1"
    return rescored


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"experience-memory-benchmark-{report['run_id']}-{report['policy_mode']}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    aggregate = report["aggregate"]
    lines = [
        "# DREAM Track 1 Experience Memory Benchmark",
        "",
        f"- Run: `{report['run_id']}`",
        f"- Policy: `{report['policy_mode']}`",
        f"- Provider/model: `{report['provider']}` / `{report['model']}`",
        f"- Cases: {report['case_count']}",
        f"- Overall score: {aggregate['overall_score']:.1f}/100",
        f"- Passed cases: {aggregate['passed_cases']}/{report['case_count']}",
        "- Case pass contract: proposal/action, memory identity recall, zero forbidden "
        "leakage, and token-budget compliance; payload/key metrics remain diagnostic.",
        "",
        "## Aggregate",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Qwen curator proposal accuracy | {aggregate['proposal_accuracy']:.1%} |",
        f"| Action accuracy | {aggregate['action_accuracy']:.1%} |",
        f"| Memory payload accuracy | {aggregate['memory_payload_accuracy']:.1%} |",
        f"| Exact canonical key accuracy | {aggregate['exact_canonical_key_accuracy']:.1%} |",
        f"| Critical memory recall | {aggregate['critical_memory_recall']:.1%} |",
        f"| Forbidden memory leak rate | {aggregate['forbidden_memory_leak_rate']:.1%} |",
        f"| Token budget compliance | {aggregate['token_budget_compliance']:.1%} |",
        f"| Stateless carryover recall | {aggregate['stateless_baseline_carryover_recall']:.1%} |",
        "",
        "## Cases",
        "",
        "| Case | Category | Result | Recall | Leaks | Tokens |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for case in report["cases"]:
        recall = case["recall"]
        lines.append(
            f"| {case['id']} | {case['category']} | "
            f"{'PASS' if case['passed'] else 'FAIL'} | {recall['recall']:.1%} | "
            f"{len(recall['leaked_values'])} | "
            f"{recall['estimated_tokens_used']}/{recall['token_budget']} |"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    args = parse_args()
    if args.attempts < 1:
        raise ValueError("--attempts must be at least 1.")
    if args.rescore:
        report = rescore_report(
            json.loads(args.rescore.read_text(encoding="utf-8-sig"))
        )
    else:
        load_env_file(args.env_file)
        cases = load_cases(args.cases)
        report = run_benchmark(cases, policy_mode=args.policy, attempts=args.attempts)
    json_path, markdown_path = write_reports(report, args.output_dir)
    print(f"Experience benchmark: {report['aggregate']['overall_score']:.1f}/100")
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    return 0 if report["aggregate"]["passed_cases"] == report["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
