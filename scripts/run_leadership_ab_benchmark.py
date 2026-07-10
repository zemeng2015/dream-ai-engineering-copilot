# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dream.core.paths import ensure_artifacts_dir  # noqa: E402
from dream.leadership_demo import (  # noqa: E402
    LeadershipBenchmarkFixtureProvider,
    LeadershipBenchmarkSuiteRunner,
    LeadershipDemoService,
    load_approved_pricing_manifest,
    load_approved_sme_reference,
    write_benchmark_suite_report,
)
from dream.leadership_demo.service import LEADERSHIP_DEMO_PROFILE_ID  # noqa: E402
from dream.llm import OpenAICompatibleProvider  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the provider-neutral same-model DREAM leadership A/B benchmark. "
            "The fixture validates the harness only; use openai-compatible for live-model evidence."
        )
    )
    parser.add_argument(
        "--provider",
        choices=["fixture", "openai-compatible"],
        default="fixture",
    )
    parser.add_argument(
        "--model",
        help="Optional model override for the OpenAI-compatible provider.",
    )
    parser.add_argument(
        "--sme-reference-manifest",
        type=Path,
        help=(
            "Optional approved SME manifest with reviewer, approval time, reference path, "
            "and SHA-256 proof."
        ),
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Paired repetitions; each repetition makes two provider calls (default: 3).",
    )
    parser.add_argument(
        "--pricing-manifest",
        type=Path,
        help=(
            "Optional approved provider/model pricing manifest. Cost remains not_measured "
            "without exact provider/model and input/output token proof."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ensure_artifacts_dir() / "leadership-benchmark",
    )
    args = parser.parse_args()

    demo_service = LeadershipDemoService()
    seeded = demo_service.seed(reset=True)
    snapshot = demo_service.requirement_repository.get(seeded.case_id)
    if args.provider == "fixture":
        provider = LeadershipBenchmarkFixtureProvider()
        evidence_tier = "harness_validation"
    else:
        provider = OpenAICompatibleProvider(model_name=args.model)
        evidence_tier = "live_model_evidence"
    reference = None
    reference_proof = None
    if args.sme_reference_manifest:
        reference, reference_proof = load_approved_sme_reference(
            args.sme_reference_manifest
        )
    pricing_proof = (
        load_approved_pricing_manifest(args.pricing_manifest)
        if args.pricing_manifest
        else None
    )
    report = LeadershipBenchmarkSuiteRunner(
        provider=provider,
        evidence_tier=evidence_tier,
        pricing_proof=pricing_proof,
    ).run(
        snapshot=snapshot,
        profile_id=LEADERSHIP_DEMO_PROFILE_ID,
        repetitions=args.repetitions,
        sme_reference=reference,
        sme_reference_proof=reference_proof,
    )
    json_path, markdown_path = write_benchmark_suite_report(
        report,
        output_dir=args.output_dir,
    )
    print(report.model_dump_json(indent=2, exclude={"runs"}))
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
