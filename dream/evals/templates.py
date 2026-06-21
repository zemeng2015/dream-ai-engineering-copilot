# SPDX-License-Identifier: Apache-2.0

from dream.evals.models import EvaluationScorecard


def render_scorecard_report(scorecard: EvaluationScorecard) -> str:
    lines = [
        "# DREAM Evaluation Scorecard",
        "",
        "## Summary",
        f"- Evaluation ID: {scorecard.evaluation_id}",
        f"- Target Type: {scorecard.target_type}",
        f"- Target ID: {scorecard.target_id or 'n/a'}",
        f"- Overall Score: {scorecard.overall_score:.2f}",
        f"- Grade: {scorecard.grade}",
        f"- Pass Status: {scorecard.pass_status}",
        "",
        "## Dimensions",
    ]
    for dimension in scorecard.dimensions:
        lines.extend(
            [
                f"### {dimension.name}",
                f"- Score: {dimension.score:.2f}",
                f"- Weight: {dimension.weight:.2f}",
                f"- Passed: {str(dimension.passed).lower()}",
                f"- Rationale: {dimension.rationale}",
            ]
        )
        lines.append("- Evidence:")
        lines.extend(f"  - {item}" for item in dimension.evidence or ["No evidence recorded."])
        lines.append("- Missing Items:")
        lines.extend(f"  - {item}" for item in dimension.missing_items or ["None"])
        lines.append("- Recommendations:")
        lines.extend(f"  - {item}" for item in dimension.recommendations or ["None"])
        lines.append("")

    lines.extend(
        [
            "## Source Coverage",
            *[
                f"- {name}: {str(value).lower()}"
                for name, value in sorted(scorecard.source_coverage.items())
            ],
            "",
            "## Missing Critical Items",
            *[f"- {item}" for item in scorecard.missing_critical_items or ["None"]],
            "",
            "## Hallucination Warnings",
            *[f"- {item}" for item in scorecard.hallucination_warnings or ["None"]],
            "",
            "## Recommendations",
            *[f"- {item}" for item in scorecard.recommendations or ["None"]],
        ]
    )
    return "\n".join(lines) + "\n"
