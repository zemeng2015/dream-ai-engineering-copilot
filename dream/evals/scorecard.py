# SPDX-License-Identifier: Apache-2.0

from dream.evals.models import EvaluationDimension

REQUIREMENT_DIMENSION_WEIGHTS = {
    "completeness": 1.2,
    "evidence_quality": 1.4,
    "impact_accuracy": 1.2,
    "role_coverage": 1.0,
    "test_awareness": 1.0,
    "historical_context": 1.0,
    "actionability": 1.1,
    "specificity": 1.0,
    "hallucination_risk": 1.2,
}

PR_REVIEW_DIMENSION_WEIGHTS = {
    "changed_file_awareness": 1.2,
    "codebase_memory_usage": 1.3,
    "business_alignment": 1.0,
    "test_gap_detection": 1.2,
    "operational_risk_awareness": 1.0,
    "historical_context": 1.0,
    "actionability": 1.0,
    "hallucination_risk": 1.2,
}

TESTGEN_DIMENSION_WEIGHTS = {
    "target_selection_quality": 1.1,
    "validation_clarity": 1.0,
    "coverage_reporting": 1.0,
    "human_review_readiness": 1.3,
    "safety": 1.3,
    "actionability": 1.0,
}


def make_dimension(
    *,
    name: str,
    score: float,
    weight: float,
    rationale: str,
    evidence: list[str] | None = None,
    missing_items: list[str] | None = None,
    recommendations: list[str] | None = None,
) -> EvaluationDimension:
    normalized_score = clamp_score(score)
    return EvaluationDimension(
        name=name,
        score=normalized_score,
        weight=weight,
        passed=normalized_score >= 7.0,
        rationale=rationale,
        evidence=evidence or [],
        missing_items=missing_items or [],
        recommendations=recommendations or [],
    )


def clamp_score(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 2)


def weighted_average(dimensions: list[EvaluationDimension]) -> float:
    if not dimensions:
        return 0.0
    total_weight = sum(item.weight for item in dimensions)
    return round(sum(item.score * item.weight for item in dimensions) / total_weight, 2)


def grade_for_score(score: float) -> str:
    if score >= 8.5:
        return "A"
    if score >= 7.0:
        return "B"
    if score >= 5.5:
        return "C"
    if score >= 4.0:
        return "D"
    return "F"


def pass_status_for_score(score: float, missing_critical_items: list[str]) -> str:
    if score >= 7.0 and not missing_critical_items:
        return "pass"
    if score >= 5.5:
        return "warning"
    return "fail"


def score_fraction(present_count: int, total_count: int, *, empty_score: float = 6.0) -> float:
    if total_count == 0:
        return empty_score
    return clamp_score(10.0 * present_count / total_count)
