# SPDX-License-Identifier: Apache-2.0

from datetime import UTC, datetime
from uuid import uuid4

from dream.memory.models import MemoryEvalResult, MemoryScanResult
from dream.memory.repository import MemoryDistillationRepository


class MemoryDistillationEvaluator:
    def __init__(self, repository: MemoryDistillationRepository | None = None) -> None:
        self.repository = repository or MemoryDistillationRepository()

    def evaluate(self, *, team_id: str, scan_id: str = "latest") -> MemoryEvalResult:
        scan = self.repository.load_scan(team_id, scan_id)
        result = self.evaluate_scan(scan)
        self.repository.save_eval(result)
        return result

    @staticmethod
    def evaluate_scan(scan: MemoryScanResult) -> MemoryEvalResult:
        recommendations: list[str] = []
        validation = scan.validation
        if validation.citation_validity < 1.0:
            recommendations.append("Fix missing or stale source spans before review.")
        if validation.unsupported_claim_rate > 0.03:
            recommendations.append("Tighten extraction prompts and evidence-span validation.")
        if validation.secret_leakage_count:
            recommendations.append("Block or quarantine sensitive sources before durable memory.")
        if validation.auto_promoted_semantic_claims:
            recommendations.append("Keep semantic claims as candidates until human review.")
        if not recommendations:
            recommendations.append("Memory scan passes MVP guardrails.")

        pass_status = (
            "pass"
            if validation.citation_validity == 1.0
            and validation.unsupported_claim_rate <= 0.03
            and validation.secret_leakage_count == 0
            and validation.auto_promoted_semantic_claims == 0
            else "fail"
        )
        evaluation_id = f"memory-eval-{uuid4().hex[:12]}"
        markdown = MemoryDistillationEvaluator._markdown_report(
            scan=scan,
            evaluation_id=evaluation_id,
            pass_status=pass_status,
            recommendations=recommendations,
        )
        return MemoryEvalResult(
            evaluation_id=evaluation_id,
            scan_id=scan.scan_id,
            team_id=scan.team_id,
            repo_name=scan.repo_name,
            created_at=datetime.now(UTC).isoformat(),
            citation_validity=validation.citation_validity,
            unsupported_claim_rate=validation.unsupported_claim_rate,
            secret_leakage_count=validation.secret_leakage_count,
            structural_claims=validation.structural_claims,
            semantic_candidate_claims=validation.semantic_candidate_claims,
            auto_promoted_semantic_claims=validation.auto_promoted_semantic_claims,
            pass_status=pass_status,
            recommendations=recommendations,
            markdown_report=markdown,
        )

    @staticmethod
    def _markdown_report(
        *,
        scan: MemoryScanResult,
        evaluation_id: str,
        pass_status: str,
        recommendations: list[str],
    ) -> str:
        validation = scan.validation
        provenance = scan.provenance
        recommendation_lines = "\n".join(f"- {item}" for item in recommendations)
        return f"""# Memory Distillation Eval

- Evaluation: `{evaluation_id}`
- Scan: `{scan.scan_id}`
- Schema: `{scan.schema_version}`
- Team: `{scan.team_id}`
- Repo: `{scan.repo_name or "_team"}`
- Commit: `{provenance.commit_sha if provenance else "unknown"}`
- Dirty: `{provenance.dirty if provenance else "unknown"}`
- Status: `{pass_status}`

## Guardrails

| Metric | Value |
| --- | ---: |
| Citation validity | {validation.citation_validity:.2f} |
| Unsupported claim rate | {validation.unsupported_claim_rate:.2f} |
| Secret leakage count | {validation.secret_leakage_count} |
| Structural claims | {validation.structural_claims} |
| Semantic candidate claims | {validation.semantic_candidate_claims} |
| Auto-promoted semantic claims | {validation.auto_promoted_semantic_claims} |

## Recommendations

{recommendation_lines}
"""
