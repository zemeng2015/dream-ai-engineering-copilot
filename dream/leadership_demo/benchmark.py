# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from dream.core.errors import DreamError
from dream.dlp import ensure_dlp_guarded_provider
from dream.evals.evidence import EvalProfileLoader
from dream.evals.models import EvalProfile
from dream.llm import BaseLLMProvider, LLMResponse
from dream.requirement_cases.models import ContextEvidence, RequirementCaseSnapshot

BENCHMARK_SCENARIO_ID = "leadership-async-status-v1"
BENCHMARK_CONTRACT_VERSION = "engineering-decision-v1"


class BenchmarkStatement(BaseModel):
    statement: str
    citations: list[str] = Field(default_factory=list)


class BenchmarkQuestion(BaseModel):
    role: str
    question: str
    citations: list[str] = Field(default_factory=list)


class LeadershipBenchmarkOutput(BaseModel):
    intent_summary: str
    impact_areas: list[BenchmarkStatement] = Field(default_factory=list)
    critical_questions: list[BenchmarkQuestion] = Field(default_factory=list)
    test_targets: list[BenchmarkStatement] = Field(default_factory=list)
    historical_risks: list[BenchmarkStatement] = Field(default_factory=list)
    unsupported_assumptions: list[str] = Field(default_factory=list)


class BenchmarkSource(BaseModel):
    source_id: str
    source_type: str
    source_path: str
    title: str
    excerpt: str
    memory_claim_id: str | None = None
    governance_status: str | None = None
    reviewed_by: str | None = None


class CoverageMetric(BaseModel):
    hits: list[str] = Field(default_factory=list)
    misses: list[str] = Field(default_factory=list)
    recall: float


class CitationMetric(BaseModel):
    total: int
    valid: int
    invalid: int
    validity_rate: float | None = None


class OptionalMeasurement(BaseModel):
    status: Literal["measured", "not_measured"]
    value: float | int | None = None
    unit: str | None = None
    note: str


class BenchmarkArmResult(BaseModel):
    arm: Literal["stateless", "dream"]
    context_enabled: bool
    source_count: int
    prompt_hash: str
    raw_output_hash: str
    token_usage: dict[str, int] | None = None
    output: LeadershipBenchmarkOutput | None = None
    parse_error: str | None = None
    citations: CitationMetric
    source_impact_recall: CoverageMetric
    source_test_recall: CoverageMetric
    source_history_recall: CoverageMetric
    impact_recall: CoverageMetric
    critical_question_recall: CoverageMetric
    test_recall: CoverageMetric
    history_recall: CoverageMetric
    unsupported_claims: int
    latency: OptionalMeasurement
    tokens: OptionalMeasurement
    cost: OptionalMeasurement
    human_edit_distance: OptionalMeasurement


class BenchmarkDelta(BaseModel):
    valid_citations: int
    impact_recall: float
    critical_question_recall: float
    test_recall: float
    history_recall: float
    unsupported_claims: int


class SMEReferenceProof(BaseModel):
    reviewer: str
    approved_at: str
    manifest_hash: str
    reference_hash: str


class SMEReferenceManifest(BaseModel):
    scenario_id: str
    contract_version: str
    status: Literal["draft", "approved"]
    reviewer: str | None = None
    approved_at: str | None = None
    reference_json: str
    reference_sha256: str


class ProviderPricingProof(BaseModel):
    schema_version: Literal["provider-pricing-v1"] = "provider-pricing-v1"
    provider: str
    model: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    input_cost_per_million_tokens: float = Field(ge=0)
    output_cost_per_million_tokens: float = Field(ge=0)
    effective_at: str
    approved_by: str
    approved_at: str
    source_reference: str
    manifest_hash: str


class ProviderPricingManifest(BaseModel):
    schema_version: Literal["provider-pricing-v1"]
    status: Literal["draft", "approved"]
    provider: str
    model: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    input_cost_per_million_tokens: float = Field(ge=0)
    output_cost_per_million_tokens: float = Field(ge=0)
    effective_at: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    source_reference: str | None = None


class LeadershipBenchmarkReport(BaseModel):
    scenario_id: str = BENCHMARK_SCENARIO_ID
    contract_version: str = BENCHMARK_CONTRACT_VERSION
    evidence_tier: Literal["harness_validation", "live_model_evidence"]
    provider: str
    model: str
    request_hash: str
    output_contract_hash: str
    same_provider_verified: bool
    same_model_verified: bool
    same_request_verified: bool = True
    same_contract_verified: bool = True
    arm_order: list[Literal["stateless", "dream"]]
    sme_reference_proof: SMEReferenceProof | None = None
    pricing_proof: ProviderPricingProof | None = None
    stateless: BenchmarkArmResult
    dream: BenchmarkArmResult
    delta: BenchmarkDelta
    limitations: list[str] = Field(default_factory=list)


class DistributionSummary(BaseModel):
    count: int
    mean: float
    median: float
    minimum: float
    maximum: float


class PairedMetricAggregate(BaseModel):
    status: Literal["measured", "partial", "not_measured"]
    unit: str
    stateless: DistributionSummary | None = None
    dream: DistributionSummary | None = None
    delta: DistributionSummary | None = None
    note: str


class LeadershipBenchmarkSuiteReport(BaseModel):
    scenario_id: str = BENCHMARK_SCENARIO_ID
    contract_version: str = BENCHMARK_CONTRACT_VERSION
    evidence_tier: Literal["harness_validation", "live_model_evidence"]
    provider: str
    model: str
    repetitions: int
    same_provider_verified: bool
    same_model_verified: bool
    same_request_verified: bool
    same_contract_verified: bool
    sme_reference_proof: SMEReferenceProof | None = None
    pricing_proof: ProviderPricingProof | None = None
    runs: list[LeadershipBenchmarkReport]
    aggregates: dict[str, PairedMetricAggregate]
    limitations: list[str] = Field(default_factory=list)


class LeadershipBenchmarkFixtureProvider:
    """Deterministic harness fixture; never product or ROI evidence."""

    provider_name = "benchmark-fixture"
    model_name = "deterministic-context-transform-v1"

    def complete(self, prompt: str) -> LLMResponse:
        sources = _sources_from_prompt(prompt)
        output = self._output(sources)
        text = output.model_dump_json()
        return LLMResponse(
            text=text,
            model_name=self.model_name,
            provider_name=self.provider_name,
            token_usage={
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(text.split()),
            },
        )

    @staticmethod
    def _output(sources: list[BenchmarkSource]) -> LeadershipBenchmarkOutput:
        if not sources:
            return LeadershipBenchmarkOutput(
                intent_summary="Improve visibility for a long-running forecast request.",
                impact_areas=[
                    BenchmarkStatement(statement="Update the user interface."),
                    BenchmarkStatement(statement="Review backend status handling."),
                ],
                critical_questions=[
                    BenchmarkQuestion(
                        role="Engineering",
                        question="What should happen when the request is slow?",
                    )
                ],
                test_targets=[BenchmarkStatement(statement="Add suitable regression tests.")],
                historical_risks=[BenchmarkStatement(statement="Long-running work may time out.")],
                unsupported_assumptions=[
                    "The current platform status model is not available to this arm."
                ],
            )

        claim_source = next(
            (item for item in sources if item.memory_claim_id),
            sources[0],
        )
        impact_areas = [
            BenchmarkStatement(
                statement=f"Inspect {Path(item.source_path).name} for execution-status impact.",
                citations=[item.source_id],
            )
            for item in sources
            if Path(item.source_path).suffix in {".java", ".ts", ".py"}
            and "test" not in item.source_path.lower()
        ][:8]
        test_targets = [
            BenchmarkStatement(
                statement=f"Cover {Path(item.source_path).name} in regression validation.",
                citations=[item.source_id],
            )
            for item in sources
            if _looks_like_test(item.source_path)
        ][:6]
        historical_risks = [
            BenchmarkStatement(
                statement=f"Reconcile the change with {Path(item.source_path).stem}.",
                citations=[item.source_id],
            )
            for item in sources
            if _looks_historical(item.source_path)
        ][:6]
        questions = [
            ("BA", "What status labels should users see?"),
            ("TL", "Should SERVICE_TASK and BATCH_TASK share the same status model?"),
            ("FE", "Should the Execution Monitor poll or subscribe to updates?"),
            ("BE", "What is the authoritative source for task status?"),
            ("QA", "What are the regression tests for stuck RUNNING state?"),
            ("OPS", "What runbook update is needed for stuck execution?"),
        ]
        return LeadershipBenchmarkOutput(
            intent_summary=(
                "Expose task-level execution status and bounded automatic refresh for "
                "long-running forecast work."
            ),
            impact_areas=impact_areas,
            critical_questions=[
                BenchmarkQuestion(
                    role=role,
                    question=question,
                    citations=[claim_source.source_id],
                )
                for role, question in questions
            ],
            test_targets=test_targets,
            historical_risks=historical_risks,
        )


class LeadershipBenchmarkRunner:
    def __init__(
        self,
        *,
        provider: BaseLLMProvider,
        evidence_tier: Literal["harness_validation", "live_model_evidence"],
        profile_loader: EvalProfileLoader | None = None,
        pricing_proof: ProviderPricingProof | None = None,
    ) -> None:
        self.provider = ensure_dlp_guarded_provider(provider)
        self.evidence_tier = evidence_tier
        self.profile_loader = profile_loader or EvalProfileLoader()
        self.pricing_proof = pricing_proof

    def run(
        self,
        *,
        snapshot: RequirementCaseSnapshot,
        profile_id: str,
        sme_reference: LeadershipBenchmarkOutput | None = None,
        sme_reference_proof: SMEReferenceProof | None = None,
        arm_order: tuple[Literal["stateless", "dream"], ...] = (
            "stateless",
            "dream",
        ),
    ) -> LeadershipBenchmarkReport:
        if len(arm_order) != 2 or set(arm_order) != {"stateless", "dream"}:
            raise DreamError("Benchmark arm order must contain stateless and dream once each.")
        profile = self.profile_loader.load(snapshot.case.team_id, profile_id)
        sources = _benchmark_sources(snapshot.evidence)
        prompts = {
            "stateless": _render_prompt(snapshot.case.raw_request, []),
            "dream": _render_prompt(snapshot.case.raw_request, sources),
        }
        responses: dict[str, LLMResponse] = {}
        durations: dict[str, int] = {}
        for arm in arm_order:
            response, duration_ms = self._complete(prompts[arm])
            responses[arm] = response
            durations[arm] = duration_ms
        stateless_response = responses["stateless"]
        dream_response = responses["dream"]
        if stateless_response.provider_name != dream_response.provider_name:
            raise DreamError("Benchmark arms did not use the same provider.")
        if stateless_response.model_name != dream_response.model_name:
            raise DreamError("Benchmark arms did not use the same model.")
        self._validate_pricing(stateless_response)

        stateless = _evaluate_arm(
            arm="stateless",
            response=stateless_response,
            prompt=prompts["stateless"],
            latency_ms=durations["stateless"],
            sources=[],
            profile=profile,
            sme_reference=sme_reference,
            sme_reference_proof=sme_reference_proof,
            pricing_proof=self.pricing_proof,
        )
        dream = _evaluate_arm(
            arm="dream",
            response=dream_response,
            prompt=prompts["dream"],
            latency_ms=durations["dream"],
            sources=sources,
            profile=profile,
            sme_reference=sme_reference,
            sme_reference_proof=sme_reference_proof,
            pricing_proof=self.pricing_proof,
        )
        limitations = [
            (
                "The scenario and golden profile use synthetic DemoCorp/DFP data; "
                "this is not a production ROI claim."
            ),
            (
                "Human edit distance is only measured when an approved, hash-verified "
                "SME reference manifest is supplied."
            ),
        ]
        if self.pricing_proof is None:
            limitations.append(
                "Cost is not reported without an approved, versioned provider pricing manifest."
            )
        if self.evidence_tier == "harness_validation":
            limitations.insert(
                0,
                (
                    "Fixture results validate the paired harness and metrics only; "
                    "they are not model-quality evidence."
                ),
            )
        return LeadershipBenchmarkReport(
            evidence_tier=self.evidence_tier,
            provider=stateless_response.provider_name,
            model=stateless_response.model_name,
            request_hash=_hash(snapshot.case.raw_request),
            output_contract_hash=_hash(_contract_json()),
            same_provider_verified=True,
            same_model_verified=True,
            arm_order=list(arm_order),
            sme_reference_proof=sme_reference_proof,
            pricing_proof=self.pricing_proof,
            stateless=stateless,
            dream=dream,
            delta=BenchmarkDelta(
                valid_citations=dream.citations.valid - stateless.citations.valid,
                impact_recall=round(dream.impact_recall.recall - stateless.impact_recall.recall, 4),
                critical_question_recall=round(
                    dream.critical_question_recall.recall
                    - stateless.critical_question_recall.recall,
                    4,
                ),
                test_recall=round(dream.test_recall.recall - stateless.test_recall.recall, 4),
                history_recall=round(
                    dream.history_recall.recall - stateless.history_recall.recall,
                    4,
                ),
                unsupported_claims=(dream.unsupported_claims - stateless.unsupported_claims),
            ),
            limitations=limitations,
        )

    def _complete(self, prompt: str) -> tuple[LLMResponse, int]:
        started = perf_counter()
        response = self.provider.complete(prompt)
        duration_ms = max(1, round((perf_counter() - started) * 1000))
        return response, duration_ms

    def _validate_pricing(self, response: LLMResponse) -> None:
        if self.pricing_proof is None:
            return
        if self.pricing_proof.provider != response.provider_name:
            raise DreamError("Pricing provider does not match the resolved benchmark provider.")
        if self.pricing_proof.model != response.model_name:
            raise DreamError("Pricing model does not match the resolved benchmark model.")


class LeadershipBenchmarkSuiteRunner:
    def __init__(
        self,
        *,
        provider: BaseLLMProvider,
        evidence_tier: Literal["harness_validation", "live_model_evidence"],
        profile_loader: EvalProfileLoader | None = None,
        pricing_proof: ProviderPricingProof | None = None,
    ) -> None:
        self.runner = LeadershipBenchmarkRunner(
            provider=provider,
            evidence_tier=evidence_tier,
            profile_loader=profile_loader,
            pricing_proof=pricing_proof,
        )

    def run(
        self,
        *,
        snapshot: RequirementCaseSnapshot,
        profile_id: str,
        repetitions: int,
        sme_reference: LeadershipBenchmarkOutput | None = None,
        sme_reference_proof: SMEReferenceProof | None = None,
    ) -> LeadershipBenchmarkSuiteReport:
        if repetitions < 1:
            raise DreamError("Benchmark repetitions must be at least 1.")
        runs = []
        for index in range(repetitions):
            order: tuple[Literal["stateless", "dream"], ...] = (
                ("stateless", "dream") if index % 2 == 0 else ("dream", "stateless")
            )
            runs.append(
                self.runner.run(
                    snapshot=snapshot,
                    profile_id=profile_id,
                    sme_reference=sme_reference,
                    sme_reference_proof=sme_reference_proof,
                    arm_order=order,
                )
            )
        providers = {run.provider for run in runs}
        models = {run.model for run in runs}
        if len(providers) != 1:
            raise DreamError("Benchmark repetitions did not use one provider.")
        if len(models) != 1:
            raise DreamError("Benchmark repetitions did not use one model.")
        limitations = list(dict.fromkeys(item for run in runs for item in run.limitations))
        limitations.append(
            "Each repetition makes two provider calls; arm order alternates to reduce order bias."
        )
        return LeadershipBenchmarkSuiteReport(
            evidence_tier=runs[0].evidence_tier,
            provider=runs[0].provider,
            model=runs[0].model,
            repetitions=repetitions,
            same_provider_verified=True,
            same_model_verified=True,
            same_request_verified=all(run.same_request_verified for run in runs),
            same_contract_verified=all(run.same_contract_verified for run in runs),
            sme_reference_proof=sme_reference_proof,
            pricing_proof=runs[0].pricing_proof,
            runs=runs,
            aggregates=_aggregate_runs(runs),
            limitations=limitations,
        )


def write_benchmark_report(
    report: LeadershipBenchmarkReport,
    *,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "leadership-ab-benchmark.json"
    markdown_path = output_dir / "leadership-ab-benchmark.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(_render_report(report), encoding="utf-8")
    return json_path, markdown_path


def write_benchmark_suite_report(
    report: LeadershipBenchmarkSuiteReport,
    *,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "leadership-ab-benchmark-suite.json"
    markdown_path = output_dir / "leadership-ab-benchmark-suite.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(_render_suite_report(report), encoding="utf-8")
    return json_path, markdown_path


def load_sme_reference(path: Path) -> LeadershipBenchmarkOutput:
    return LeadershipBenchmarkOutput.model_validate_json(path.read_text(encoding="utf-8"))


def load_approved_sme_reference(
    manifest_path: Path,
) -> tuple[LeadershipBenchmarkOutput, SMEReferenceProof]:
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = SMEReferenceManifest.model_validate(yaml.safe_load(manifest_text) or {})
    if manifest.status != "approved":
        raise DreamError("SME reference manifest must have status approved.")
    if not manifest.reviewer or not manifest.approved_at:
        raise DreamError("Approved SME reference requires reviewer and approved_at.")
    if manifest.scenario_id != BENCHMARK_SCENARIO_ID:
        raise DreamError("SME reference scenario does not match the benchmark scenario.")
    if manifest.contract_version != BENCHMARK_CONTRACT_VERSION:
        raise DreamError("SME reference contract version does not match the benchmark contract.")
    raw_reference_path = Path(manifest.reference_json)
    if raw_reference_path.is_absolute():
        raise DreamError("SME reference_json must be relative to its manifest.")
    manifest_dir = manifest_path.parent.resolve()
    reference_path = (manifest_dir / raw_reference_path).resolve()
    if not reference_path.is_relative_to(manifest_dir):
        raise DreamError("SME reference_json escapes the manifest directory.")
    reference_text = reference_path.read_text(encoding="utf-8")
    reference_hash = _hash(reference_text)
    expected_hash = manifest.reference_sha256.removeprefix("sha256:")
    if expected_hash != reference_hash:
        raise DreamError("SME reference hash does not match the approved manifest.")
    reference = LeadershipBenchmarkOutput.model_validate_json(reference_text)
    return reference, SMEReferenceProof(
        reviewer=manifest.reviewer,
        approved_at=manifest.approved_at,
        manifest_hash=_hash(manifest_text),
        reference_hash=reference_hash,
    )


def load_approved_pricing_manifest(path: Path) -> ProviderPricingProof:
    manifest_text = path.read_text(encoding="utf-8")
    manifest = ProviderPricingManifest.model_validate(yaml.safe_load(manifest_text) or {})
    if manifest.status != "approved":
        raise DreamError("Provider pricing manifest must have status approved.")
    required = {
        "effective_at": manifest.effective_at,
        "approved_by": manifest.approved_by,
        "approved_at": manifest.approved_at,
        "source_reference": manifest.source_reference,
    }
    missing = [key for key, value in required.items() if not value or not value.strip()]
    if missing:
        raise DreamError("Approved provider pricing manifest is missing: " + ", ".join(missing))
    return ProviderPricingProof(
        provider=manifest.provider,
        model=manifest.model,
        currency=manifest.currency,
        input_cost_per_million_tokens=manifest.input_cost_per_million_tokens,
        output_cost_per_million_tokens=manifest.output_cost_per_million_tokens,
        effective_at=manifest.effective_at or "",
        approved_by=manifest.approved_by or "",
        approved_at=manifest.approved_at or "",
        source_reference=manifest.source_reference or "",
        manifest_hash=_hash(manifest_text),
    )


def _benchmark_sources(evidence: list[ContextEvidence]) -> list[BenchmarkSource]:
    ordered = sorted(
        evidence,
        key=lambda item: (
            0 if item.memory_claim_id else 1,
            -item.relevance_score,
            item.source_path,
            item.evidence_id,
        ),
    )
    return [
        BenchmarkSource(
            source_id=f"SRC-{index:03d}",
            source_type=item.source_type,
            source_path=item.source_path,
            title=item.title,
            excerpt=item.excerpt[:600],
            memory_claim_id=item.memory_claim_id,
            governance_status=item.governance_status,
            reviewed_by=item.reviewed_by,
        )
        for index, item in enumerate(ordered, start=1)
    ]


def _render_prompt(request: str, sources: list[BenchmarkSource]) -> str:
    return f"""DREAM paired leadership benchmark

The organization request, instructions, output contract, and model settings are identical
for both arms. Treat the source catalog below as the only organization-specific evidence.
If the catalog is empty, do not invent organization facts or citations.

ORGANIZATION REQUEST
{request}

OUTPUT RULES
- Return one JSON object and no prose outside JSON.
- Use source_id values exactly as supplied in the source catalog.
- Every organization-specific impact, test, question, or historical risk needs citations.
- When evidence supplies exact code or test filenames, include those filenames verbatim in
  the relevant impact_areas or test_targets statement.
- When evidence supplies incident, Jira, or PR identifiers, include those identifiers verbatim
  in the relevant historical_risks statement.
- Put uncertain claims in unsupported_assumptions instead of presenting them as facts.

OUTPUT CONTRACT ({BENCHMARK_CONTRACT_VERSION})
{_contract_json()}

BEGIN SOURCE CATALOG
{json.dumps([item.model_dump() for item in sources], indent=2)}
END SOURCE CATALOG
"""


def _contract_json() -> str:
    return json.dumps(LeadershipBenchmarkOutput.model_json_schema(), sort_keys=True)


def _evaluate_arm(
    *,
    arm: Literal["stateless", "dream"],
    response: LLMResponse,
    prompt: str,
    latency_ms: int,
    sources: list[BenchmarkSource],
    profile: EvalProfile,
    sme_reference: LeadershipBenchmarkOutput | None,
    sme_reference_proof: SMEReferenceProof | None,
    pricing_proof: ProviderPricingProof | None,
) -> BenchmarkArmResult:
    output, parse_error = _parse_output(response.text)
    allowed_ids = {item.source_id for item in sources}
    source_text = "\n".join(f"{item.source_path}\n{item.title}\n{item.excerpt}" for item in sources)
    citation_values = _all_citations(output) if output else []
    valid = [item for item in citation_values if item in allowed_ids]
    invalid = [item for item in citation_values if item not in allowed_ids]
    citation_metric = CitationMetric(
        total=len(citation_values),
        valid=len(valid),
        invalid=len(invalid),
        validity_rate=(round(len(valid) / len(citation_values), 4) if citation_values else None),
    )
    impact_text = _statements_text(output.impact_areas) if output else ""
    question_texts = [item.question for item in output.critical_questions] if output else []
    test_text = _statements_text(output.test_targets) if output else ""
    history_text = _statements_text(output.historical_risks) if output else ""
    unsupported_claims = _unsupported_count(output, allowed_ids) if output else 0
    token_total = _token_total(response.token_usage)
    return BenchmarkArmResult(
        arm=arm,
        context_enabled=bool(sources),
        source_count=len(sources),
        prompt_hash=_hash(prompt),
        raw_output_hash=_hash(response.text),
        token_usage=response.token_usage,
        output=output,
        parse_error=parse_error,
        citations=citation_metric,
        source_impact_recall=_coverage(source_text, profile.expected_code),
        source_test_recall=_coverage(source_text, profile.expected_tests),
        source_history_recall=_coverage(
            source_text,
            [*profile.expected_incidents, *profile.expected_jira, *profile.expected_pr],
        ),
        impact_recall=_coverage(impact_text, profile.expected_code),
        critical_question_recall=_question_coverage(
            question_texts,
            [item for values in profile.critical_questions.values() for item in values],
        ),
        test_recall=_coverage(test_text, profile.expected_tests),
        history_recall=_coverage(
            history_text,
            [*profile.expected_incidents, *profile.expected_jira, *profile.expected_pr],
        ),
        unsupported_claims=unsupported_claims,
        latency=OptionalMeasurement(
            status="measured",
            value=latency_ms,
            unit="ms",
            note="Wall-clock provider completion duration for this single arm.",
        ),
        tokens=OptionalMeasurement(
            status="measured" if token_total is not None else "not_measured",
            value=token_total,
            unit="tokens" if token_total is not None else None,
            note=(
                "Provider-reported token usage."
                if token_total is not None
                else "The provider did not return token usage."
            ),
        ),
        cost=_cost_measurement(
            response.token_usage,
            pricing_proof,
        ),
        human_edit_distance=_human_edit_measurement(
            output,
            sme_reference,
            sme_reference_proof,
        ),
    )


def _parse_output(text: str) -> tuple[LeadershipBenchmarkOutput | None, str | None]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        return None, "Provider output did not contain a JSON object."
    try:
        payload = json.loads(cleaned[start : end + 1])
        return LeadershipBenchmarkOutput.model_validate(payload), None
    except (json.JSONDecodeError, ValidationError) as exc:
        return None, f"Output contract validation failed: {exc}"


def _all_citations(output: LeadershipBenchmarkOutput) -> list[str]:
    citations: list[str] = []
    for item in [*output.impact_areas, *output.test_targets, *output.historical_risks]:
        citations.extend(item.citations)
    for item in output.critical_questions:
        citations.extend(item.citations)
    return citations


def _unsupported_count(
    output: LeadershipBenchmarkOutput,
    allowed_ids: set[str],
) -> int:
    items = [*output.impact_areas, *output.test_targets, *output.historical_risks]
    question_citations = [item.citations for item in output.critical_questions]
    unsupported = sum(
        1
        for citations in [*(item.citations for item in items), *question_citations]
        if not citations or any(citation not in allowed_ids for citation in citations)
    )
    return unsupported + len(output.unsupported_assumptions)


def _coverage(text: str, expected: list[str]) -> CoverageMetric:
    normalized = text.lower()
    hits = [item for item in expected if item.lower() in normalized]
    misses = [item for item in expected if item not in hits]
    return CoverageMetric(
        hits=hits,
        misses=misses,
        recall=round(len(hits) / len(expected), 4) if expected else 1.0,
    )


def _question_coverage(questions: list[str], expected: list[str]) -> CoverageMetric:
    question_terms = [_terms(question) for question in questions]
    hits = []
    for item in expected:
        expected_terms = _terms(item)
        if not expected_terms:
            continue
        matched = any(
            len(candidate & expected_terms) >= 2
            and len(candidate & expected_terms) / len(expected_terms) >= 0.6
            for candidate in question_terms
        )
        if matched:
            hits.append(item)
    misses = [item for item in expected if item not in hits]
    return CoverageMetric(
        hits=hits,
        misses=misses,
        recall=round(len(hits) / len(expected), 4) if expected else 1.0,
    )


def _human_edit_measurement(
    output: LeadershipBenchmarkOutput | None,
    reference: LeadershipBenchmarkOutput | None,
    proof: SMEReferenceProof | None,
) -> OptionalMeasurement:
    if output is None or reference is None or proof is None:
        return OptionalMeasurement(
            status="not_measured",
            note="No approved, hash-verified SME reference manifest was supplied.",
        )
    ratio = SequenceMatcher(
        None,
        output.model_dump_json(),
        reference.model_dump_json(),
    ).ratio()
    return OptionalMeasurement(
        status="measured",
        value=round(1.0 - ratio, 4),
        unit="normalized_edit_distance",
        note="Character-sequence distance from the supplied SME-reviewed contract output.",
    )


def _token_total(usage: dict[str, int] | None) -> int | None:
    if not usage:
        return None
    if "total_tokens" in usage:
        return usage["total_tokens"]
    values = [
        value
        for key, value in usage.items()
        if key in {"prompt_tokens", "completion_tokens", "input_tokens", "output_tokens"}
    ]
    return sum(values) if values else None


def _cost_measurement(
    usage: dict[str, int] | None,
    pricing: ProviderPricingProof | None,
) -> OptionalMeasurement:
    if pricing is None:
        return OptionalMeasurement(
            status="not_measured",
            note="No approved, versioned provider pricing manifest was supplied.",
        )
    if not usage:
        return OptionalMeasurement(
            status="not_measured",
            note="Provider returned no token usage; approved pricing could not be applied.",
        )
    input_tokens = _first_token_value(usage, "prompt_tokens", "input_tokens")
    output_tokens = _first_token_value(usage, "completion_tokens", "output_tokens")
    if input_tokens is None or output_tokens is None:
        return OptionalMeasurement(
            status="not_measured",
            note=(
                "Provider did not return separate input and output token counts; "
                "total tokens are insufficient for the approved pricing rates."
            ),
        )
    cost = (
        input_tokens * pricing.input_cost_per_million_tokens
        + output_tokens * pricing.output_cost_per_million_tokens
    ) / 1_000_000
    return OptionalMeasurement(
        status="measured",
        value=round(cost, 8),
        unit=pricing.currency,
        note=(
            f"{input_tokens} input tokens at "
            f"{pricing.currency} {pricing.input_cost_per_million_tokens:g} per million; "
            f"{output_tokens} output tokens at "
            f"{pricing.currency} {pricing.output_cost_per_million_tokens:g} per million."
        ),
    )


def _first_token_value(usage: dict[str, int], *keys: str) -> int | None:
    for key in keys:
        if key in usage:
            return usage[key]
    return None


def _sources_from_prompt(prompt: str) -> list[BenchmarkSource]:
    match = re.search(
        r"BEGIN SOURCE CATALOG\s*(\[.*\])\s*END SOURCE CATALOG",
        prompt,
        flags=re.DOTALL,
    )
    if not match:
        return []
    payload = json.loads(match.group(1))
    return [BenchmarkSource.model_validate(item) for item in payload]


def _statements_text(items: list[BenchmarkStatement]) -> str:
    return "\n".join(item.statement for item in items)


def _terms(value: str) -> set[str]:
    stop = {
        "a",
        "an",
        "and",
        "are",
        "be",
        "for",
        "in",
        "is",
        "of",
        "or",
        "same",
        "share",
        "should",
        "the",
        "to",
        "what",
    }
    aliases = {
        "derived": "derive",
        "events": "event",
        "labels": "label",
        "persisted": "persist",
        "polling": "poll",
        "regressions": "regression",
        "running": "run",
        "statuses": "status",
        "subscribing": "subscribe",
        "tasks": "task",
        "tests": "test",
        "transitions": "transition",
        "updates": "update",
        "users": "user",
    }
    tokens = re.findall(r"[a-z0-9]+", value.lower().replace("_", " ").replace("-", " "))
    return {aliases.get(item, item) for item in tokens if item not in stop and len(item) > 1}


def _looks_like_test(path: str) -> bool:
    normalized = path.lower()
    return any(value in normalized for value in ["src/test", "tests/", "test.java", ".spec.ts"])


def _looks_historical(path: str) -> bool:
    normalized = path.lower()
    return any(value in normalized for value in ["inc-", "dfp-", "pr-", "incidents", "historical-"])


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _aggregate_runs(
    runs: list[LeadershipBenchmarkReport],
) -> dict[str, PairedMetricAggregate]:
    cost_unit = runs[0].pricing_proof.currency if runs and runs[0].pricing_proof else "currency"
    cost_note = (
        "Calculated from the approved exact-provider/model pricing manifest and "
        "per-arm input/output token counts."
        if runs and runs[0].pricing_proof
        else "Not measured until an approved, versioned pricing manifest is supplied."
    )
    metric_specs = {
        "valid_citations": (
            lambda arm: float(arm.citations.valid),
            "count",
            "Citations that resolve to the arm's supplied source catalog.",
        ),
        "citation_validity_rate": (
            lambda arm: arm.citations.validity_rate,
            "ratio",
            "Valid citations divided by all emitted citations; absent when no citation exists.",
        ),
        "impact_recall": (
            lambda arm: arm.impact_recall.recall,
            "ratio",
            "Expected code impacts recovered from the frozen synthetic profile.",
        ),
        "source_catalog_impact_recall": (
            lambda arm: arm.source_impact_recall.recall,
            "ratio",
            "Expected code impacts available to the model in the source catalog.",
        ),
        "critical_question_recall": (
            lambda arm: arm.critical_question_recall.recall,
            "ratio",
            "Expected role-specific questions recovered.",
        ),
        "test_recall": (
            lambda arm: arm.test_recall.recall,
            "ratio",
            "Expected test targets recovered.",
        ),
        "source_catalog_test_recall": (
            lambda arm: arm.source_test_recall.recall,
            "ratio",
            "Expected test targets available to the model in the source catalog.",
        ),
        "history_recall": (
            lambda arm: arm.history_recall.recall,
            "ratio",
            "Expected incident, Jira, and PR history recovered.",
        ),
        "source_catalog_history_recall": (
            lambda arm: arm.source_history_recall.recall,
            "ratio",
            "Expected history identifiers available to the model in the source catalog.",
        ),
        "unsupported_claims": (
            lambda arm: float(arm.unsupported_claims),
            "count",
            (
                "Output items without valid support plus declared unsupported assumptions; "
                "lower is better."
            ),
        ),
        "latency": (
            lambda arm: _measurement_number(arm.latency),
            "ms",
            "Wall-clock provider completion time per arm.",
        ),
        "tokens": (
            lambda arm: _measurement_number(arm.tokens),
            "tokens",
            "Provider-reported token use when available.",
        ),
        "human_edit_distance": (
            lambda arm: _measurement_number(arm.human_edit_distance),
            "normalized_edit_distance",
            "Distance from the approved SME reference; lower is better.",
        ),
        "cost": (
            lambda arm: _measurement_number(arm.cost),
            cost_unit,
            cost_note,
        ),
    }
    return {
        name: _aggregate_metric(runs, getter=getter, unit=unit, note=note)
        for name, (getter, unit, note) in metric_specs.items()
    }


def _aggregate_metric(
    runs: list[LeadershipBenchmarkReport],
    *,
    getter,
    unit: str,
    note: str,
) -> PairedMetricAggregate:
    stateless_values = [value for run in runs if (value := getter(run.stateless)) is not None]
    dream_values = [value for run in runs if (value := getter(run.dream)) is not None]
    paired_values = [
        (stateless, dream)
        for run in runs
        if (stateless := getter(run.stateless)) is not None
        and (dream := getter(run.dream)) is not None
    ]
    if not stateless_values and not dream_values:
        status = "not_measured"
    elif len(stateless_values) == len(runs) and len(dream_values) == len(runs):
        status = "measured"
    else:
        status = "partial"
    return PairedMetricAggregate(
        status=status,
        unit=unit,
        stateless=_distribution(stateless_values),
        dream=_distribution(dream_values),
        delta=_distribution([dream - stateless for stateless, dream in paired_values]),
        note=note,
    )


def _distribution(values: list[float]) -> DistributionSummary | None:
    if not values:
        return None
    return DistributionSummary(
        count=len(values),
        mean=round(mean(values), 8),
        median=round(median(values), 8),
        minimum=round(min(values), 8),
        maximum=round(max(values), 8),
    )


def _measurement_number(measurement: OptionalMeasurement) -> float | None:
    if measurement.status != "measured" or measurement.value is None:
        return None
    return float(measurement.value)


def _render_report(report: LeadershipBenchmarkReport) -> str:
    stateless = report.stateless
    dream = report.dream
    lines = [
        "# DREAM Leadership Paired A/B Benchmark",
        "",
        f"Evidence tier: **{report.evidence_tier}**  ",
        f"Provider/model: `{report.provider}` / `{report.model}`  ",
        f"Scenario: `{report.scenario_id}`  ",
        "",
        "Both arms used the same provider, model, organization request, and JSON output contract. "
        "The only intentional variable was whether the approved DREAM source catalog was supplied.",
        "",
        "| Metric | Stateless | DREAM | Delta |",
        "|---|---:|---:|---:|",
        (
            f"| Valid citations | {stateless.citations.valid} | "
            f"{dream.citations.valid} | {report.delta.valid_citations:+d} |"
        ),
        (
            f"| Impact recall | {stateless.impact_recall.recall:.1%} | "
            f"{dream.impact_recall.recall:.1%} | {report.delta.impact_recall:+.1%} |"
        ),
        (
            "| Critical-question recall | "
            f"{stateless.critical_question_recall.recall:.1%} | "
            f"{dream.critical_question_recall.recall:.1%} | "
            f"{report.delta.critical_question_recall:+.1%} |"
        ),
        (
            f"| Test recall | {stateless.test_recall.recall:.1%} | "
            f"{dream.test_recall.recall:.1%} | {report.delta.test_recall:+.1%} |"
        ),
        (
            f"| History recall | {stateless.history_recall.recall:.1%} | "
            f"{dream.history_recall.recall:.1%} | {report.delta.history_recall:+.1%} |"
        ),
        (
            f"| Unsupported claims | {stateless.unsupported_claims} | "
            f"{dream.unsupported_claims} | {report.delta.unsupported_claims:+d} |"
        ),
        f"| Latency | {stateless.latency.value} ms | {dream.latency.value} ms | n/a |",
        (
            f"| Tokens | {_measurement_value(stateless.tokens)} | "
            f"{_measurement_value(dream.tokens)} | n/a |"
        ),
        (
            "| Human edit distance | "
            f"{_measurement_value(stateless.human_edit_distance)} | "
            f"{_measurement_value(dream.human_edit_distance)} | n/a |"
        ),
        f"| Cost | {_measurement_value(stateless.cost)} | {_measurement_value(dream.cost)} | n/a |",
        "",
        "## Retrieval ceiling",
        "",
        "These metrics measure what the source catalog made available before generation.",
        "",
        "| Catalog metric | Stateless | DREAM |",
        "|---|---:|---:|",
        (
            f"| Impact source recall | {stateless.source_impact_recall.recall:.1%} | "
            f"{dream.source_impact_recall.recall:.1%} |"
        ),
        (
            f"| Test source recall | {stateless.source_test_recall.recall:.1%} | "
            f"{dream.source_test_recall.recall:.1%} |"
        ),
        (
            f"| History source recall | {stateless.source_history_recall.recall:.1%} | "
            f"{dream.source_history_recall.recall:.1%} |"
        ),
        "",
        "## Integrity checks",
        "",
        f"- Same provider: `{report.same_provider_verified}`",
        f"- Same model: `{report.same_model_verified}`",
        f"- Same request: `{report.same_request_verified}`",
        f"- Same output contract: `{report.same_contract_verified}`",
        f"- Approved pricing manifest: `{report.pricing_proof is not None}`",
        "",
        "## Limitations",
        "",
        *(f"- {item}" for item in report.limitations),
        "",
    ]
    return "\n".join(lines)


def _render_suite_report(report: LeadershipBenchmarkSuiteReport) -> str:
    lines = [
        "# DREAM Leadership Paired A/B Benchmark Suite",
        "",
        f"Evidence tier: **{report.evidence_tier}**  ",
        f"Provider/model: `{report.provider}` / `{report.model}`  ",
        f"Repetitions: **{report.repetitions}** ({report.repetitions * 2} provider calls)  ",
        "",
        "Arm order alternates by repetition. Every run uses the same organization request "
        "and output contract; only the approved DREAM source catalog changes.",
        "",
        "| Metric | Status | Stateless mean [range] | DREAM mean [range] | Delta mean |",
        "|---|---|---:|---:|---:|",
    ]
    for name, aggregate in report.aggregates.items():
        lines.append(
            f"| {name.replace('_', ' ')} | {aggregate.status} | "
            f"{_distribution_value(aggregate.stateless)} | "
            f"{_distribution_value(aggregate.dream)} | "
            f"{_distribution_value(aggregate.delta, range_value=False)} |"
        )
    lines.extend(
        [
            "",
            "## Run order",
            "",
            *(
                f"- Run {index}: {' -> '.join(run.arm_order)}"
                for index, run in enumerate(report.runs, start=1)
            ),
            "",
            "## Integrity checks",
            "",
            f"- Same provider: `{report.same_provider_verified}`",
            f"- Same model: `{report.same_model_verified}`",
            f"- Same request: `{report.same_request_verified}`",
            f"- Same output contract: `{report.same_contract_verified}`",
            f"- Approved SME reference: `{report.sme_reference_proof is not None}`",
            f"- Approved pricing manifest: `{report.pricing_proof is not None}`",
            "",
            "## Limitations",
            "",
            *(f"- {item}" for item in report.limitations),
            "",
        ]
    )
    return "\n".join(lines)


def _distribution_value(
    value: DistributionSummary | None,
    *,
    range_value: bool = True,
) -> str:
    if value is None:
        return "not measured"
    if not range_value:
        return f"{value.mean:g}"
    return f"{value.mean:g} [{value.minimum:g}, {value.maximum:g}]"


def _measurement_value(measurement: OptionalMeasurement) -> str:
    if measurement.status == "not_measured":
        return "not measured"
    return f"{measurement.value} {measurement.unit or ''}".strip()
