# SPDX-License-Identifier: Apache-2.0

import hashlib
from pathlib import Path

import pytest

from dream.core.errors import DreamError
from dream.leadership_demo import (
    LeadershipBenchmarkFixtureProvider,
    LeadershipBenchmarkOutput,
    LeadershipBenchmarkRunner,
    LeadershipBenchmarkSuiteRunner,
    LeadershipDemoService,
    ProviderPricingProof,
    SMEReferenceProof,
    load_approved_pricing_manifest,
    load_approved_sme_reference,
    write_benchmark_report,
    write_benchmark_suite_report,
)
from dream.leadership_demo.service import LEADERSHIP_DEMO_PROFILE_ID
from dream.llm import LLMResponse


def _seeded_snapshot(tmp_path: Path):
    service = LeadershipDemoService(
        artifacts_dir=tmp_path / "artifacts",
        db_path=tmp_path / "leadership.sqlite",
    )
    result = service.seed(reset=True)
    return service.requirement_repository.get(result.case_id)


def test_fixture_benchmark_proves_pair_integrity_without_claiming_model_evidence(
    tmp_path: Path,
) -> None:
    snapshot = _seeded_snapshot(tmp_path)
    report = LeadershipBenchmarkRunner(
        provider=LeadershipBenchmarkFixtureProvider(),
        evidence_tier="harness_validation",
    ).run(snapshot=snapshot, profile_id=LEADERSHIP_DEMO_PROFILE_ID)

    assert report.same_provider_verified
    assert report.same_model_verified
    assert report.same_request_verified
    assert report.same_contract_verified
    assert report.arm_order == ["stateless", "dream"]
    assert report.evidence_tier == "harness_validation"
    assert report.stateless.source_count == 0
    assert report.dream.source_count == len(snapshot.evidence)
    assert report.dream.citations.valid > report.stateless.citations.valid
    assert report.dream.critical_question_recall.recall > 0
    assert report.dream.unsupported_claims < report.stateless.unsupported_claims
    assert report.stateless.cost.status == "not_measured"
    assert report.dream.human_edit_distance.status == "not_measured"
    assert any("not model-quality evidence" in item for item in report.limitations)
    assert report.dream.output is not None
    assert report.dream.parse_error is None

    json_path, markdown_path = write_benchmark_report(
        report,
        output_dir=tmp_path / "report",
    )
    assert json_path.exists()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "same provider, model, organization request" in markdown
    assert "harness_validation" in markdown

    suite = LeadershipBenchmarkSuiteRunner(
        provider=LeadershipBenchmarkFixtureProvider(),
        evidence_tier="harness_validation",
    ).run(
        snapshot=snapshot,
        profile_id=LEADERSHIP_DEMO_PROFILE_ID,
        repetitions=3,
    )
    assert suite.repetitions == 3
    assert [run.arm_order for run in suite.runs] == [
        ["stateless", "dream"],
        ["dream", "stateless"],
        ["stateless", "dream"],
    ]
    assert suite.aggregates["impact_recall"].status == "measured"
    assert suite.aggregates["impact_recall"].dream is not None
    assert suite.aggregates["impact_recall"].dream.count == 3
    assert suite.aggregates["human_edit_distance"].status == "not_measured"
    suite_json, suite_markdown = write_benchmark_suite_report(
        suite,
        output_dir=tmp_path / "suite",
    )
    assert suite_json.exists()
    assert "Run 2: dream -> stateless" in suite_markdown.read_text(encoding="utf-8")

    proof = SMEReferenceProof(
        reviewer="Unit Test SME",
        approved_at="2026-07-10T12:00:00Z",
        manifest_hash="a" * 64,
        reference_hash="b" * 64,
    )
    assert report.dream.output is not None
    measured = LeadershipBenchmarkRunner(
        provider=LeadershipBenchmarkFixtureProvider(),
        evidence_tier="harness_validation",
    ).run(
        snapshot=snapshot,
        profile_id=LEADERSHIP_DEMO_PROFILE_ID,
        sme_reference=report.dream.output,
        sme_reference_proof=proof,
    )
    assert measured.dream.human_edit_distance.status == "measured"
    assert measured.dream.human_edit_distance.value == 0


class _ChangingModelProvider:
    provider_name = "test-provider"
    model_name = "unstable"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            text=(
                '{"intent_summary":"x","impact_areas":[],"critical_questions":[],'
                '"test_targets":[],"historical_risks":[],"unsupported_assumptions":[]}'
            ),
            provider_name=self.provider_name,
            model_name=f"model-{self.calls}",
        )


def test_benchmark_rejects_different_models_between_arms(tmp_path: Path) -> None:
    snapshot = _seeded_snapshot(tmp_path)
    with pytest.raises(DreamError, match="same model"):
        LeadershipBenchmarkRunner(
            provider=_ChangingModelProvider(),
            evidence_tier="live_model_evidence",
        ).run(snapshot=snapshot, profile_id=LEADERSHIP_DEMO_PROFILE_ID)


def test_sme_reference_requires_approved_hash_verified_manifest(tmp_path: Path) -> None:
    reference = LeadershipBenchmarkOutput(
        intent_summary="SME-approved bounded status-tracking intent.",
    )
    reference_text = reference.model_dump_json(indent=2)
    reference_path = tmp_path / "reference.json"
    reference_path.write_text(reference_text, encoding="utf-8")
    reference_hash = hashlib.sha256(reference_text.encode("utf-8")).hexdigest()
    manifest_path = tmp_path / "reference.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "scenario_id: leadership-async-status-v1",
                "contract_version: engineering-decision-v1",
                "status: draft",
                "reviewer: Forecast Platform SME",
                "approved_at: '2026-07-10T12:00:00Z'",
                "reference_json: reference.json",
                f"reference_sha256: sha256:{reference_hash}",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(DreamError, match="status approved"):
        load_approved_sme_reference(manifest_path)

    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            "status: draft",
            "status: approved",
        ),
        encoding="utf-8",
    )
    loaded, proof = load_approved_sme_reference(manifest_path)
    assert loaded == reference
    assert proof.reviewer == "Forecast Platform SME"
    assert proof.reference_hash == reference_hash

    reference_path.write_text(reference_text + "\n", encoding="utf-8")
    with pytest.raises(DreamError, match="hash"):
        load_approved_sme_reference(manifest_path)


def test_pricing_requires_approved_exact_provider_model_and_token_breakdown(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "pricing.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "schema_version: provider-pricing-v1",
                "status: draft",
                "provider: benchmark-fixture",
                "model: deterministic-context-transform-v1",
                "currency: USD",
                "input_cost_per_million_tokens: 1.25",
                "output_cost_per_million_tokens: 3.5",
                "effective_at: '2026-07-10T00:00:00Z'",
                "approved_by: Benchmark Evidence Owner",
                "approved_at: '2026-07-10T12:00:00Z'",
                "source_reference: internal-pricing-approval-test",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(DreamError, match="status approved"):
        load_approved_pricing_manifest(manifest_path)
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            "status: draft",
            "status: approved",
        ),
        encoding="utf-8",
    )
    pricing = load_approved_pricing_manifest(manifest_path)
    assert pricing.currency == "USD"
    assert pricing.manifest_hash

    snapshot = _seeded_snapshot(tmp_path)
    report = LeadershipBenchmarkRunner(
        provider=LeadershipBenchmarkFixtureProvider(),
        evidence_tier="harness_validation",
        pricing_proof=pricing,
    ).run(snapshot=snapshot, profile_id=LEADERSHIP_DEMO_PROFILE_ID)
    assert report.pricing_proof == pricing
    assert report.stateless.cost.status == "measured"
    assert report.dream.cost.status == "measured"
    assert report.dream.cost.value > report.stateless.cost.value
    assert report.dream.cost.unit == "USD"
    assert report.dream.token_usage is not None
    assert "prompt_tokens" in report.dream.token_usage
    suite = LeadershipBenchmarkSuiteRunner(
        provider=LeadershipBenchmarkFixtureProvider(),
        evidence_tier="harness_validation",
        pricing_proof=pricing,
    ).run(
        snapshot=snapshot,
        profile_id=LEADERSHIP_DEMO_PROFILE_ID,
        repetitions=2,
    )
    assert suite.aggregates["cost"].status == "measured"
    assert suite.aggregates["cost"].unit == "USD"
    assert suite.aggregates["cost"].dream is not None
    assert suite.aggregates["cost"].dream.count == 2
    assert "Calculated from the approved" in suite.aggregates["cost"].note

    mismatch = pricing.model_copy(update={"model": "different-model"})
    with pytest.raises(DreamError, match="Pricing model"):
        LeadershipBenchmarkRunner(
            provider=LeadershipBenchmarkFixtureProvider(),
            evidence_tier="harness_validation",
            pricing_proof=mismatch,
        ).run(snapshot=snapshot, profile_id=LEADERSHIP_DEMO_PROFILE_ID)


class _TotalOnlyUsageProvider:
    provider_name = "benchmark-fixture"
    model_name = "deterministic-context-transform-v1"

    def complete(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            text=(
                '{"intent_summary":"x","impact_areas":[],"critical_questions":[],'
                '"test_targets":[],"historical_risks":[],"unsupported_assumptions":[]}'
            ),
            provider_name=self.provider_name,
            model_name=self.model_name,
            token_usage={"total_tokens": 100},
        )


def test_cost_stays_unmeasured_when_provider_returns_only_total_tokens(tmp_path: Path) -> None:
    snapshot = _seeded_snapshot(tmp_path)
    pricing = ProviderPricingProof(
        provider="benchmark-fixture",
        model="deterministic-context-transform-v1",
        currency="USD",
        input_cost_per_million_tokens=1.0,
        output_cost_per_million_tokens=2.0,
        effective_at="2026-07-10T00:00:00Z",
        approved_by="Evidence Owner",
        approved_at="2026-07-10T12:00:00Z",
        source_reference="test",
        manifest_hash="a" * 64,
    )
    report = LeadershipBenchmarkRunner(
        provider=_TotalOnlyUsageProvider(),
        evidence_tier="harness_validation",
        pricing_proof=pricing,
    ).run(snapshot=snapshot, profile_id=LEADERSHIP_DEMO_PROFILE_ID)

    assert report.stateless.tokens.status == "measured"
    assert report.stateless.cost.status == "not_measured"
    assert "separate input and output" in report.stateless.cost.note
