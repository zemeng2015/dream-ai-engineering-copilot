# SPDX-License-Identifier: Apache-2.0

import re

from dream.memory.models import (
    MemoryClaim,
    MemoryClaimRetrievalBatch,
    MemoryClaimSearchResult,
)
from dream.memory.repository import MemoryDistillationRepository

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


class MemoryClaimRetriever:
    def __init__(self, repository: MemoryDistillationRepository | None = None) -> None:
        self.repository = repository or MemoryDistillationRepository()

    def search(
        self,
        *,
        team_id: str,
        query: str,
        scan_id: str = "latest",
        top_k: int = 8,
    ) -> list[MemoryClaimSearchResult]:
        return self.search_with_policy(
            team_id=team_id,
            query=query,
            scan_id=scan_id,
            top_k=top_k,
        ).results

    def search_with_policy(
        self,
        *,
        team_id: str,
        query: str,
        scan_id: str = "latest",
        top_k: int = 8,
    ) -> MemoryClaimRetrievalBatch:
        scan = self.repository.load_scan(team_id, scan_id)
        review_statuses = self.repository.latest_review_statuses(team_id)
        unresolved_conflict_claim_ids = self._unresolved_conflict_claim_ids(
            team_id=team_id,
            scan_id=scan.scan_id,
        )
        blocked_claim_ids = {
            claim.claim_id
            for claim in scan.claims
            if claim.claim_id in unresolved_conflict_claim_ids
            and (
                review_statuses[claim.claim_id].new_status
                if claim.claim_id in review_statuses
                else claim.governance.status
            )
            == "approved"
        }
        terms = self._tokens(query)
        scored: list[MemoryClaimSearchResult] = []
        for claim in scan.claims:
            effective_status = review_statuses.get(claim.claim_id)
            status = effective_status.new_status if effective_status else claim.governance.status
            if status != "approved":
                continue
            if claim.claim_id in blocked_claim_ids:
                continue
            score = self._score_claim(claim, terms)
            if score <= 0:
                continue
            scored.append(
                MemoryClaimSearchResult(
                    claim=claim,
                    effective_status=status,
                    score=float(score),
                    reason="Approved memory claim matched query terms.",
                    review_event=effective_status,
                )
            )
        results = sorted(
            scored,
            key=lambda item: (-item.score, item.claim.entity.canonical_name, item.claim.claim_id),
        )[:top_k]
        blocked = sorted(blocked_claim_ids)
        warnings = []
        if blocked:
            warnings.append(
                "Approved memory claims were blocked because their conflicts are unresolved: "
                + ", ".join(blocked)
            )
        return MemoryClaimRetrievalBatch(
            results=results,
            blocked_claim_ids=blocked,
            warnings=warnings,
        )

    def context_card(
        self,
        *,
        team_id: str,
        query: str,
        scan_id: str = "latest",
        top_k: int = 8,
    ) -> str:
        results = self.search(team_id=team_id, query=query, scan_id=scan_id, top_k=top_k)
        lines = [
            "# DREAM Memory Context Card",
            "",
            f"- Team: `{team_id}`",
            f"- Scan: `{scan_id}`",
            f"- Query: {query}",
            f"- Approved claims: {len(results)}",
            "",
            "## Approved Claims",
            "",
        ]
        if not results:
            lines.append("_No approved memory claims matched._")
            return "\n".join(lines).rstrip() + "\n"
        for result in results:
            claim = result.claim
            evidence_paths = ", ".join(span.path for span in claim.evidence.spans[:3])
            relation_value = claim.relation.value or claim.relation.object_entity_id or "_"
            lines.extend(
                [
                    (
                        f"- `{claim.claim_id}` {claim.entity.canonical_name} "
                        f"--{claim.relation.type}--> {relation_value}"
                    ),
                    f"  - score: {result.score:.1f}",
                    f"  - evidence: {evidence_paths or 'missing'}",
                    f"  - method: {claim.extraction.method}",
                ]
            )
            if claim.evidence.intake_proofs:
                proof = claim.evidence.intake_proofs[0]
                lines.append(
                    f"  - intake proof: {proof.document_id} / {len(proof.section_proofs)} sections"
                )
        return "\n".join(lines).rstrip() + "\n"

    @classmethod
    def _score_claim(cls, claim: MemoryClaim, terms: list[str]) -> int:
        if not terms:
            return 1
        text = " ".join(
            [
                claim.entity.canonical_name,
                " ".join(claim.entity.aliases),
                claim.entity.entity_type,
                claim.relation.type,
                claim.relation.value or "",
                claim.relation.object_entity_id or "",
                claim.relation.condition or "",
                " ".join(span.path for span in claim.evidence.spans),
                " ".join(span.source_type for span in claim.evidence.spans),
            ]
        )
        text_terms = cls._tokens(text)
        return sum(3 if term in text_terms else 0 for term in terms)

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return [token.lower() for token in TOKEN_RE.findall(value)]

    def _unresolved_conflict_claim_ids(
        self,
        *,
        team_id: str,
        scan_id: str,
    ) -> set[str]:
        # Imported lazily because the distillation service imports the memory models
        # used by this retriever. Conflict policy remains defined in one place.
        from dream.memory.distiller import MemoryDistillationService

        report = MemoryDistillationService(repository=self.repository).conflicts(
            team_id=team_id,
            scan_id=scan_id,
        )
        return {side.claim.claim_id for pair in report.pairs for side in (pair.left, pair.right)}
