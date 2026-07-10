# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import re
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dream.core.errors import ProviderRequestError  # noqa: E402
from dream.evals.evidence import EvalProfileLoader  # noqa: E402
from dream.evals.models import EvalProfile  # noqa: E402
from dream.llm.qwen_cloud import QwenCloudProvider  # noqa: E402
from dream.memory.retriever import EngineeringMemoryRetriever  # noqa: E402
from dream.requirement_cases.models import ContextEvidence  # noqa: E402

DEFAULT_PROOF_DIR = ROOT / "artifacts" / "qwencloud-proof"
DEFAULT_RUN_DIR = ROOT / "artifacts" / "qwencloud-benchmarks"
ALLOWED_ENV_KEYS = {
    "DASHSCOPE_API_KEY",
    "QWEN_API_KEY",
    "QWEN_BASE_URL",
    "DASHSCOPE_BASE_URL",
    "QWEN_MODEL",
    "QWEN_TIMEOUT_SECONDS",
}
REQUIRED_SECTIONS = (
    "Evidence-Backed Recommendation",
    "Impacted Components",
    "Test Strategy",
    "Risks and Open Questions",
    "Sources Used",
    "Human Review",
)
SOURCE_FIELDS = (
    "expected_code",
    "expected_tests",
    "expected_docs",
    "expected_incidents",
    "expected_jira",
    "expected_pr",
)
REFERENCE_PATTERN = re.compile(
    r"\b(?:INC|DFP|PR)-\d{3,}\b|"
    r"\b[A-Za-z0-9_][A-Za-z0-9_.-]*\.(?:java|ts|py|md)\b",
    re.IGNORECASE,
)

BENCHMARK_CASES = (
    {
        "profile_id": "async-status-tracking",
        "request_path": "examples/requirement-requests/async-status-tracking.md",
    },
    {
        "profile_id": "output-collection-idempotency",
        "request": (
            "Make output collection safe to retry without creating duplicate artifacts. "
            "Cover the idempotency boundary, regression tests, operational detection, and "
            "questions that must be resolved before implementation."
        ),
    },
    {
        "profile_id": "task-config-validation",
        "request_path": "examples/requirement-requests/task-config-validation.md",
    },
    {
        "profile_id": "partial-execution-recovery",
        "request_path": "examples/requirement-requests/partial-execution-recovery.md",
    },
    {
        "profile_id": "workflow-versioning",
        "request_path": "examples/requirement-requests/workflow-versioning.md",
    },
    {
        "profile_id": "operator-retry-action",
        "request_path": "examples/requirement-requests/operator-retry-action.md",
    },
    {
        "profile_id": "large-output-preview",
        "request_path": "examples/requirement-requests/large-output-preview.md",
    },
)


def load_env_file(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Environment file not found: {path}")
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


def load_markdown_section(path: Path, heading: str) -> str:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    marker = f"## {heading}".lower()
    start = next(
        (index + 1 for index, line in enumerate(lines) if line.strip().lower() == marker),
        None,
    )
    if start is None:
        raise ValueError(f"Missing section '{heading}' in {path}")
    selected = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        selected.append(line)
    value = " ".join(line.strip() for line in selected if line.strip())
    if not value:
        raise ValueError(f"Empty section '{heading}' in {path}")
    return value


def case_request(case: dict[str, str]) -> str:
    request_path = case.get("request_path")
    if request_path:
        return load_markdown_section(ROOT / request_path, "Request")
    return case["request"]


def normalize(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def item_present(text: str, item: str) -> bool:
    normalized_text = normalize(text)
    normalized_item = normalize(item)
    basename = normalize(Path(item.replace("\\", "/")).name)
    return bool(
        normalized_item
        and (normalized_item in normalized_text or (basename and basename in normalized_text))
    )


def score_items(text: str, items: list[str]) -> tuple[float, list[str], list[str]]:
    if not items:
        return 1.0, [], []
    present = [item for item in items if item_present(text, item)]
    missing = [item for item in items if item not in present]
    return len(present) / len(items), present, missing


def expected_sources(profile: EvalProfile) -> list[str]:
    values: list[str] = []
    for field in SOURCE_FIELDS:
        values.extend(getattr(profile, field))
    return values


def extract_references(text: str) -> list[str]:
    return sorted({match.group(0).lower() for match in REFERENCE_PATTERN.finditer(text)})


def known_references(team_id: str) -> set[str]:
    references: set[str] = set()
    pack_dir = ROOT / "knowledge_packs" / team_id
    if pack_dir.is_dir():
        for path in pack_dir.rglob("*"):
            if path.is_file():
                references.add(path.name.lower())
                references.update(extract_references(path.name))

    index_dir = ROOT / "artifacts" / "codebase-indexes" / team_id
    if index_dir.is_dir():
        for path in index_dir.glob("*.json"):
            references.update(extract_references(path.read_text(encoding="utf-8-sig")))
    return references


def evidence_references(evidence: list[ContextEvidence]) -> set[str]:
    return set(extract_references(render_evidence(evidence)))


def section_coverage(text: str) -> tuple[float, list[str], list[str]]:
    headings = {
        normalize(line.lstrip("#").strip())
        for line in text.splitlines()
        if line.lstrip().startswith("#")
    }
    present = [section for section in REQUIRED_SECTIONS if normalize(section) in headings]
    missing = [section for section in REQUIRED_SECTIONS if section not in present]
    return len(present) / len(REQUIRED_SECTIONS), present, missing


def role_coverage(text: str, roles: list[str]) -> tuple[float, list[str], list[str]]:
    present = [role for role in roles if re.search(rf"\b{re.escape(role)}\b", text, re.I)]
    missing = [role for role in roles if role not in present]
    return (len(present) / len(roles) if roles else 1.0), present, missing


def score_output(
    text: str,
    profile: EvalProfile,
    allowed_references: set[str],
    corpus_references: set[str],
) -> dict[str, Any]:
    domain_items = [*profile.expected_concepts, *profile.critical_risks]
    domain_recall, domain_present, domain_missing = score_items(text, domain_items)
    sources = expected_sources(profile)
    source_recall, sources_present, sources_missing = score_items(text, sources)
    roles_score, roles_present, roles_missing = role_coverage(text, profile.expected_roles)
    sections_score, sections_present, sections_missing = section_coverage(text)

    cited = extract_references(text)
    valid = [reference for reference in cited if reference in allowed_references]
    unseen_known = [
        reference
        for reference in cited
        if reference in corpus_references and reference not in allowed_references
    ]
    fabricated = [reference for reference in cited if reference not in corpus_references]
    unsupported = sorted({*unseen_known, *fabricated})
    unsupported_penalty = min(20.0, len(unsupported) * 4.0)
    raw_score = 100 * (
        0.35 * domain_recall
        + 0.35 * source_recall
        + 0.15 * roles_score
        + 0.15 * sections_score
    )
    overall = round(max(0.0, raw_score - unsupported_penalty), 1)
    citation_precision = round(len(valid) / len(cited), 3) if cited else None

    return {
        "grounding_score": overall,
        "domain_recall": round(domain_recall, 3),
        "expected_source_recall": round(source_recall, 3),
        "role_coverage": round(roles_score, 3),
        "section_coverage": round(sections_score, 3),
        "valid_reference_count": len(valid),
        "unsupported_reference_count": len(unsupported),
        "citation_precision": citation_precision,
        "domain_items_present": domain_present,
        "domain_items_missing": domain_missing,
        "expected_sources_present": sources_present,
        "expected_sources_missing": sources_missing,
        "roles_present": roles_present,
        "roles_missing": roles_missing,
        "sections_present": sections_present,
        "sections_missing": sections_missing,
        "valid_references": valid,
        "unseen_known_references": unseen_known,
        "fabricated_references": fabricated,
        "unsupported_references": unsupported,
        "unsupported_penalty": unsupported_penalty,
    }


def render_evidence(evidence: list[ContextEvidence]) -> str:
    blocks = []
    for index, item in enumerate(evidence, start=1):
        excerpt = " ".join(item.excerpt.split())[:600]
        blocks.append(
            "\n".join(
                [
                    f"[E{index}] Source: {item.source_path}",
                    f"Title: {item.title}",
                    f"Type: {item.source_type}",
                    f"Evidence: {excerpt}",
                ]
            )
        )
    return "\n\n".join(blocks)


def build_prompt(request: str, evidence: list[ContextEvidence] | None) -> str:
    if evidence:
        context = render_evidence(evidence)
    else:
        context = "No organization-specific evidence was provided."

    sections = "\n".join(f"## {section}" for section in REQUIRED_SECTIONS)
    return f"""Evaluate the engineering request below and produce a concise review artifact.

Fairness rules:
- Use only organization facts and source names explicitly present in the evidence block.
- When organization evidence is absent, label organization-specific details as unknown.
- Do not invent file names, incidents, Jira items, pull requests, APIs, or approval status.
- Include role-labeled open questions for every relevant role.
- Under Sources Used, cite only evidence identifiers or source paths actually provided.
- State that human review is required.

Use exactly these level-two headings:
{sections}

Engineering request:
{request}

Organization evidence:
{context}
"""


def retrieval_metrics(evidence: list[ContextEvidence], profile: EvalProfile) -> dict[str, Any]:
    gold = {item.lower() for item in expected_sources(profile)}
    relevance: list[int] = []
    retrieved_keys: set[str] = set()
    for item in evidence:
        path = item.source_path.replace("\\", "/")
        basename = path.rsplit("/", 1)[-1].lower()
        path_keys = {basename, *extract_references(path)}
        retrieved_keys.update(path_keys)
        relevance.append(int(bool(path_keys & gold)))

    exact_present = sorted(item for item in gold if item in retrieved_keys)
    exact_missing = sorted(gold - retrieved_keys)
    exact_recall = len(exact_present) / len(gold) if gold else 1.0
    exact_precision = sum(relevance) / len(evidence) if evidence else 0.0
    dcg = sum(value / math.log2(index + 2) for index, value in enumerate(relevance))
    ideal_relevant = min(sum(relevance), len(evidence))
    ideal_dcg = sum(1 / math.log2(index + 2) for index in range(ideal_relevant))
    ndcg = dcg / ideal_dcg if ideal_dcg else 0.0

    blob = "\n".join(
        f"{item.source_path}\n{item.title}\n{item.excerpt}" for item in evidence
    )
    context_recall, context_present, context_missing = score_items(
        blob, expected_sources(profile)
    )
    return {
        "exact_path_recall_at_k": round(exact_recall, 3),
        "exact_path_precision_at_k": round(exact_precision, 3),
        "ndcg_at_k": round(ndcg, 3),
        "exact_paths_present": exact_present,
        "exact_paths_missing": exact_missing,
        "context_mention_recall": round(context_recall, 3),
        "context_mentions_present": context_present,
        "context_mentions_missing": context_missing,
        "evidence_count": len(evidence),
        "evidence_paths": [item.source_path for item in evidence],
    }


def complete_with_retry(
    provider: QwenCloudProvider,
    prompt: str,
    *,
    attempts: int = 3,
) -> tuple[Any, int, int]:
    started = time.perf_counter()
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = provider.complete(prompt)
            duration_ms = int((time.perf_counter() - started) * 1000)
            return response, duration_ms, attempt
        except Exception as exc:  # noqa: BLE001 - preserve provider retry behavior
            last_error = exc
            if isinstance(exc, ProviderRequestError) and "HTTP 4" in str(exc):
                raise
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
    assert last_error is not None
    raise last_error


def aggregate(results: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    metrics = [case[mode]["metrics"] for case in results]
    token_usage = [case[mode].get("token_usage") or {} for case in results]
    return {
        "mean_grounding_score": round(
            statistics.fmean(item["grounding_score"] for item in metrics), 1
        ),
        "mean_domain_recall": round(
            statistics.fmean(item["domain_recall"] for item in metrics), 3
        ),
        "mean_expected_source_recall": round(
            statistics.fmean(item["expected_source_recall"] for item in metrics), 3
        ),
        "mean_role_coverage": round(
            statistics.fmean(item["role_coverage"] for item in metrics), 3
        ),
        "mean_section_coverage": round(
            statistics.fmean(item["section_coverage"] for item in metrics), 3
        ),
        "valid_reference_count": sum(item["valid_reference_count"] for item in metrics),
        "unsupported_reference_count": sum(
            item["unsupported_reference_count"] for item in metrics
        ),
        "total_tokens": sum(item.get("total_tokens", 0) for item in token_usage),
    }


def exact_paired_permutation_p(deltas: list[float]) -> float:
    nonzero = [delta for delta in deltas if delta != 0]
    if not nonzero:
        return 1.0
    observed = abs(statistics.fmean(nonzero))
    permutations = list(itertools.product((-1, 1), repeat=len(nonzero)))
    extreme = sum(
        1
        for signs in permutations
        if abs(
            statistics.fmean(
                delta * sign for delta, sign in zip(nonzero, signs, strict=True)
            )
        )
        >= observed - 1e-12
    )
    return extreme / len(permutations)


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_markdown(report: dict[str, Any], output_path: Path) -> None:
    baseline = report["aggregate"]["baseline"]
    dream = report["aggregate"]["dream"]
    domain_recall_delta = dream["mean_domain_recall"] - baseline["mean_domain_recall"]
    source_recall_delta = (
        dream["mean_expected_source_recall"] - baseline["mean_expected_source_recall"]
    )
    lines = [
        "# DREAM Qwen Cloud Memory A/B Benchmark",
        "",
        f"- Run: `{report['run_id']}`",
        f"- Provider: `{report['provider']}`",
        f"- Model: `{report['model']}`",
        f"- Cases: {report['case_count']}",
        "- Temperature: `0` (provider contract)",
        "- Variable changed: organization evidence absent vs DREAM-retrieved evidence",
        (
            "- Exact retrieval Recall@12: "
            f"{report['aggregate']['mean_retrieval_exact_path_recall_at_k']:.1%}"
        ),
        (
            f"- Paired result: DREAM won {report['aggregate']['dream_wins']}/"
            f"{report['case_count']} cases; median delta "
            f"{report['aggregate']['median_grounding_score_delta']:+.1f}; exact paired "
            f"permutation `p={report['aggregate']['exact_paired_permutation_p']:.4f}`"
        ),
        "",
        "## Aggregate Results",
        "",
        "| Metric | Stateless Qwen | Qwen + DREAM | Delta |",
        "|---|---:|---:|---:|",
        (
            f"| Deterministic reference score | {baseline['mean_grounding_score']:.1f} | "
            f"{dream['mean_grounding_score']:.1f} | "
            f"{report['aggregate']['grounding_score_delta']:+.1f} |"
        ),
        (
            f"| Domain/risk recall | {baseline['mean_domain_recall']:.1%} | "
            f"{dream['mean_domain_recall']:.1%} | "
            f"{domain_recall_delta:+.1%} |"
        ),
        (
            f"| Expected source recall | {baseline['mean_expected_source_recall']:.1%} | "
            f"{dream['mean_expected_source_recall']:.1%} | "
            f"{source_recall_delta:+.1%} |"
        ),
        (
            f"| Valid references | {baseline['valid_reference_count']} | "
            f"{dream['valid_reference_count']} | "
            f"{dream['valid_reference_count'] - baseline['valid_reference_count']:+d} |"
        ),
        (
            f"| Unsupported references | {baseline['unsupported_reference_count']} | "
            f"{dream['unsupported_reference_count']} | "
            f"{dream['unsupported_reference_count'] - baseline['unsupported_reference_count']:+d} |"
        ),
        "",
        "## Paired Cases",
        "",
        "| Case | Exact path Recall@12 | Baseline | DREAM | Delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['profile_id']} | "
            f"{case['retrieval']['exact_path_recall_at_k']:.1%} | "
            f"{case['baseline']['metrics']['grounding_score']:.1f} | "
            f"{case['dream']['metrics']['grounding_score']:.1f} | "
            f"{case['score_delta']:+.1f} |"
        )
    lines.extend(
        [
            "",
            "## Methodology",
            "",
            "- Seven pre-existing golden profiles define expected concepts, risks, code, tests, "
            "docs, incidents, Jira items, PRs, and roles.",
            "- Six requests are read verbatim from pre-existing BA rough-request fixtures; the "
            "seventh is a neutral request that does not expose expected identifiers.",
            "- Both conditions use the same Qwen provider, model, temperature, output contract, "
            "and deterministic scorer.",
            "- DREAM receives only retriever output; the baseline receives an explicit no-context "
            "marker.",
            "- A citation is credited only when it appears in the evidence supplied to that arm; "
            "the complete corpus only separates unseen-real from fabricated references.",
            "- Retrieval quality is reported separately with exact canonical path/ID Recall@12, "
            "Precision@12, and nDCG@12.",
            "- Call order alternates by case to reduce time-order bias.",
            "",
            "## Limitations",
            "",
            "- This is a seven-case synthetic engineering benchmark, not a production claim.",
            "- One deterministic completion per condition does not estimate sampling variance.",
            "- Exact-term scoring favors explicit, reviewable references and does not measure "
            "semantic equivalence.",
            (
                f"- {report['recovered_arm_count']} arm outputs survived an outer process timeout; "
                "their token and latency metadata were not recoverable, so those metrics are not "
                "used as comparative claims."
            ),
            "- Exact retrieval Recall@12 remains a bottleneck and bounds the achievable gain.",
            "- Human review remains required before treating generated artifacts as correct.",
            "",
            f"Machine-readable report: `{report['json_path']}`",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    profile_loader = EvalProfileLoader()
    retriever = EngineeringMemoryRetriever()
    references = known_references(args.team_id)
    selected_cases = list(BENCHMARK_CASES[: args.limit or None])
    run_id = args.resume_run or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.run_dir / run_id
    args.proof_dir.mkdir(parents=True, exist_ok=True)

    prepared: list[tuple[dict[str, str], EvalProfile, list[ContextEvidence]]] = []
    for case in selected_cases:
        profile = profile_loader.load(args.team_id, case["profile_id"])
        request = case_request(case)
        evidence = retriever.search(
            team_id=args.team_id,
            query=request,
            repo_name=args.repo_name,
            top_k=args.top_k,
        )
        prepared.append(({**case, "request": request}, profile, evidence))

    if args.dry_run:
        return {
            "run_id": run_id,
            "dry_run": True,
            "case_count": len(prepared),
            "profiles": [case[0]["profile_id"] for case in prepared],
            "retrieval": [
                {
                    "profile_id": case[0]["profile_id"],
                    **retrieval_metrics(case[2], case[1]),
                }
                for case in prepared
            ],
            "run_dir": relative_path(run_dir),
        }

    if args.resume_run:
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Benchmark run not found: {run_dir}")
    else:
        run_dir.mkdir(parents=True, exist_ok=False)
    provider = QwenCloudProvider(
        base_url=args.base_url or None,
        model_name=args.model or None,
        timeout_seconds=args.timeout_seconds,
    )
    results: list[dict[str, Any]] = []
    for index, (case, profile, evidence) in enumerate(prepared):
        case_dir = run_dir / case["profile_id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        modes = ("baseline", "dream") if index % 2 == 0 else ("dream", "baseline")
        case_result: dict[str, Any] = {
            "profile_id": case["profile_id"],
            "request": case["request"],
            "call_order": list(modes),
            "retrieval": retrieval_metrics(evidence, profile),
        }
        allowed_dream_references = evidence_references(evidence)
        for mode in modes:
            output_path = case_dir / f"{mode}.md"
            metadata_path = case_dir / f"{mode}.json"
            recovered = output_path.is_file()
            if recovered:
                response_text = output_path.read_text(encoding="utf-8")
                completion_metadata = (
                    json.loads(metadata_path.read_text(encoding="utf-8"))
                    if metadata_path.is_file()
                    else {}
                )
            else:
                prompt = build_prompt(
                    case["request"], evidence if mode == "dream" else None
                )
                response, duration_ms, attempts = complete_with_retry(provider, prompt)
                response_text = response.text.strip() + "\n"
                output_path.write_text(response_text, encoding="utf-8")
                completion_metadata = {
                    "provider": response.provider_name,
                    "model": response.model_name,
                    "duration_ms": duration_ms,
                    "attempts": attempts,
                    "token_usage": response.token_usage,
                    "completed_at": datetime.now(UTC).isoformat(),
                }
                metadata_path.write_text(
                    json.dumps(completion_metadata, indent=2), encoding="utf-8"
                )
            case_result[mode] = {
                "output_path": relative_path(output_path),
                "metrics": score_output(
                    response_text,
                    profile,
                    allowed_dream_references if mode == "dream" else set(),
                    references,
                ),
                "duration_ms": completion_metadata.get("duration_ms"),
                "attempts": completion_metadata.get("attempts"),
                "token_usage": completion_metadata.get("token_usage"),
                "recovered_from_output": recovered and not metadata_path.is_file(),
            }
        case_result["score_delta"] = round(
            case_result["dream"]["metrics"]["grounding_score"]
            - case_result["baseline"]["metrics"]["grounding_score"],
            1,
        )
        results.append(case_result)

    baseline = aggregate(results, "baseline")
    dream = aggregate(results, "dream")
    deltas = [case["score_delta"] for case in results]
    json_path = args.proof_dir / f"qwen-memory-ab-benchmark-{run_id}.json"
    markdown_path = args.proof_dir / f"qwen-memory-ab-benchmark-{run_id}.md"
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "dry_run": False,
        "provider": provider.provider_name,
        "model": provider.model_name,
        "team_id": args.team_id,
        "repo_name": args.repo_name,
        "top_k": args.top_k,
        "case_count": len(results),
        "recovered_arm_count": sum(
            int(case[mode]["recovered_from_output"])
            for case in results
            for mode in ("baseline", "dream")
        ),
        "measured_token_arm_count": sum(
            int(bool(case[mode]["token_usage"]))
            for case in results
            for mode in ("baseline", "dream")
        ),
        "methodology": {
            "temperature": 0,
            "single_variable": "organization evidence absent vs DREAM retrieval context",
            "scoring_weights": {
                "domain_and_risk_recall": 0.35,
                "expected_source_recall": 0.35,
                "role_coverage": 0.15,
                "required_section_coverage": 0.15,
            },
            "unsupported_reference_penalty": "4 points each, capped at 20",
            "reference_validation": (
                "Citations receive credit only if present in the evidence supplied to that arm; "
                "the corpus classifies unsupported refs as unseen-real or fabricated."
            ),
            "retrieval_metrics": "exact canonical path/ID Recall@K, Precision@K, and nDCG@K",
            "call_order": "alternating by case",
        },
        "aggregate": {
            "baseline": baseline,
            "dream": dream,
            "grounding_score_delta": round(
                dream["mean_grounding_score"] - baseline["mean_grounding_score"], 1
            ),
            "median_grounding_score_delta": round(statistics.median(deltas), 1),
            "exact_paired_permutation_p": round(exact_paired_permutation_p(deltas), 4),
            "dream_wins": sum(1 for case in results if case["score_delta"] > 0),
            "ties": sum(1 for case in results if case["score_delta"] == 0),
            "baseline_wins": sum(1 for case in results if case["score_delta"] < 0),
            "mean_retrieval_exact_path_recall_at_k": round(
                statistics.fmean(
                    case["retrieval"]["exact_path_recall_at_k"] for case in results
                ),
                3,
            ),
        },
        "cases": results,
        "run_dir": relative_path(run_dir),
        "json_path": relative_path(json_path),
        "markdown_path": relative_path(markdown_path),
    }
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, markdown_path)
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (run_dir / "report.md").write_text(
        markdown_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a paired stateless-Qwen vs Qwen-plus-DREAM memory benchmark."
    )
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.qwencloud.local")
    parser.add_argument("--proof-dir", type=Path, default=DEFAULT_PROOF_DIR)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--team-id", default="demo_team")
    parser.add_argument("--repo-name", default="dfp-demo-repo")
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--model", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument(
        "--resume-run",
        default="",
        help="Existing run id whose completed output files should be reused.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.top_k < 1 or args.top_k > 30:
        raise ValueError("--top-k must be between 1 and 30")
    if args.limit < 0 or args.limit > len(BENCHMARK_CASES):
        raise ValueError(f"--limit must be between 0 and {len(BENCHMARK_CASES)}")
    if not args.dry_run:
        loaded_names = load_env_file(args.env_file.resolve())
        if loaded_names:
            print(f"Loaded benchmark environment names: {', '.join(sorted(loaded_names))}")
    report = run_benchmark(args)
    if report["dry_run"]:
        print(json.dumps(report, indent=2))
    else:
        aggregate_result = report["aggregate"]
        print(f"Benchmark report: {report['markdown_path']}")
        print(
            "Deterministic reference score: "
            f"{aggregate_result['baseline']['mean_grounding_score']:.1f} -> "
            f"{aggregate_result['dream']['mean_grounding_score']:.1f} "
            f"({aggregate_result['grounding_score_delta']:+.1f})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
