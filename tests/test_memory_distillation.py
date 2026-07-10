# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase.repository import CodebaseIndexRepository
from dream.memory import (
    MemoryClaimRetriever,
    MemoryDistillationEvaluator,
    MemoryDistillationService,
)
from dream.memory.repository import MemoryDistillationRepository


def test_memory_distillation_scan_writes_source_backed_claims(tmp_path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    repository = MemoryDistillationRepository(artifacts_dir)
    service = MemoryDistillationService(
        repository=repository,
        codebase_repository=CodebaseIndexRepository(artifacts_dir),
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
    )

    scan = service.scan(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )

    assert repository.scan_path("demo_team", scan.scan_id).exists()
    assert repository.latest_scan_path("demo_team").exists()
    assert scan.sources
    assert scan.claims
    assert scan.schema_version == "memory-scan-v0.3"
    assert scan.provenance is not None
    assert scan.provenance.repo_path == "examples/java-demo-repo"
    assert scan.provenance.scanner_version == "memory-distillation-v0"
    assert any(source.commit_sha == scan.provenance.commit_sha for source in scan.sources)
    assert scan.validation.citation_validity == 1.0
    assert scan.validation.secret_leakage_count == 0
    assert scan.validation.auto_promoted_semantic_claims == 0
    assert any(claim.relation.type == "defined_in" for claim in scan.claims)
    assert any(claim.governance.status == "candidate" for claim in scan.claims)


def test_memory_distillation_diff_and_eval_guardrails(tmp_path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    repository = MemoryDistillationRepository(artifacts_dir)
    service = MemoryDistillationService(
        repository=repository,
        codebase_repository=CodebaseIndexRepository(artifacts_dir),
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
    )
    scan = service.scan(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )

    diff = service.diff_markdown(team_id="demo_team", scan_id=scan.scan_id)
    second_scan = service.scan(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )
    true_diff = service.diff(team_id="demo_team", scan_id=second_scan.scan_id)
    result = MemoryDistillationEvaluator(repository=repository).evaluate(
        team_id="demo_team",
        scan_id=scan.scan_id,
    )

    assert "# Memory Diff" in diff
    assert "Review Queue" in diff
    assert true_diff.base_scan_id == scan.scan_id
    assert true_diff.unchanged_count > 0
    assert result.pass_status == "pass"
    assert "Citation validity" in result.markdown_report


def test_memory_review_ledger_and_approved_claim_retrieval(tmp_path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    repository = MemoryDistillationRepository(artifacts_dir)
    service = MemoryDistillationService(
        repository=repository,
        codebase_repository=CodebaseIndexRepository(artifacts_dir),
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
    )
    scan = service.scan(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )
    candidate = next(
        claim
        for claim in scan.claims
        if claim.governance.status == "candidate"
        and claim.extraction.method == "heuristic_semantic"
    )
    candidate = candidate.model_copy(
        deep=True,
        update={
            "relation": candidate.relation.model_copy(
                update={"type": "current_policy", "value": "source-backed-policy"}
            ),
        },
    )
    conflicting_claim = candidate.model_copy(
        deep=True,
        update={
            "claim_id": f"{candidate.claim_id}:conflict",
            "relation": candidate.relation.model_copy(update={"value": "conflicting-value"}),
        },
    )
    claims_with_conflict = [
        claim if claim.claim_id != candidate.claim_id else candidate for claim in scan.claims
    ]
    repository.save_scan(
        scan.model_copy(update={"claims": [*claims_with_conflict, conflicting_claim]})
    )

    event = service.review_claim(
        team_id="demo_team",
        claim_id=candidate.claim_id,
        new_status="approved",
        reviewer="zack",
        reason="Validated source-backed candidate.",
        scan_id=scan.scan_id,
    )
    retrieval_before_resolution = MemoryClaimRetriever(repository=repository).search_with_policy(
        team_id="demo_team",
        query=candidate.entity.canonical_name,
        scan_id=scan.scan_id,
    )

    assert event.previous_status == "candidate"
    assert event.reviewer_signature and event.reviewer_signature.startswith("sig:")
    assert any(diff.field_path == "governance.status" for diff in event.field_diffs)
    assert event.claim_snapshot is not None
    assert event.claim_snapshot.claim_id == candidate.claim_id
    assert event.claim_snapshot.evidence_paths
    assert "semantic_claim_requires_human_review" in event.risk_signals
    assert event.conflict_signals
    assert not any(
        result.claim.claim_id == candidate.claim_id
        for result in retrieval_before_resolution.results
    )
    assert retrieval_before_resolution.blocked_claim_ids == [candidate.claim_id]
    assert "unresolved" in " ".join(retrieval_before_resolution.warnings)
    assert event.signal_explanations
    assert any(
        explanation.signal == "semantic_claim_requires_human_review"
        and "heuristic semantic extraction" in explanation.explanation
        for explanation in event.signal_explanations
    )
    assert any(
        explanation.category == "conflict" and explanation.evidence[0] == conflicting_claim.claim_id
        for explanation in event.signal_explanations
    )
    conflict_report = service.conflicts(team_id="demo_team", scan_id=scan.scan_id)
    assert conflict_report.conflict_count == 1
    pair = conflict_report.pairs[0]
    assert pair.entity_id == candidate.entity.entity_id
    assert pair.relation_type == candidate.relation.type
    assert pair.signal.category == "conflict"
    assert pair.signal.severity == "warning"
    assert {pair.left.claim.claim_id, pair.right.claim.claim_id} == {
        candidate.claim_id,
        conflicting_claim.claim_id,
    }
    assert any(
        side.effective_status == "approved"
        and side.latest_review
        and side.latest_review.event_id == event.event_id
        for side in [pair.left, pair.right]
    )
    resolution = service.resolve_conflict(
        team_id="demo_team",
        conflict_id=pair.conflict_id,
        winning_claim_id=candidate.claim_id,
        reviewer="zack",
        reason="Candidate source is authoritative.",
        scan_id=scan.scan_id,
    )
    resolved_report = service.conflicts(team_id="demo_team", scan_id=scan.scan_id)
    resolution_ledger = repository.load_conflict_resolution_ledger("demo_team")
    latest_statuses = repository.latest_review_statuses("demo_team")
    results = MemoryClaimRetriever(repository=repository).search(
        team_id="demo_team",
        query=candidate.entity.canonical_name,
        scan_id=scan.scan_id,
    )
    context_card = MemoryClaimRetriever(repository=repository).context_card(
        team_id="demo_team",
        query=candidate.entity.canonical_name,
        scan_id=scan.scan_id,
    )
    assert resolution.action == "approve_winner_reject_other"
    assert resolution.winning_claim_id == candidate.claim_id
    assert resolution.rejected_claim_id == conflicting_claim.claim_id
    assert resolution.conflict_snapshot.conflict_id == pair.conflict_id
    assert resolution.reviewer_signature and resolution.reviewer_signature.startswith("sig:")
    assert len(resolution.review_event_ids) == 2
    assert resolution_ledger.events[-1].event_id == resolution.event_id
    assert latest_statuses[candidate.claim_id].new_status == "approved"
    assert latest_statuses[conflicting_claim.claim_id].new_status == "rejected"
    assert resolved_report.conflict_count == 0
    assert repository.ledger_path("demo_team").exists()
    assert repository.conflict_resolution_ledger_path("demo_team").exists()
    assert any(result.claim.claim_id == candidate.claim_id for result in results)
    assert "DREAM Memory Context Card" in context_card


def test_memory_distillation_redacts_secret_like_previews() -> None:
    source = MemoryDistillationService._source_record(
        team_id="demo_team",
        repo_name="demo-repo",
        source_type="doc",
        path="docs/secret.md",
        content="api_key: should-not-appear\nJWT: eyJabcabcabc.eyJdefdefdef.eyJghighighi",
        indexed_at="2026-01-01T00:00:00Z",
        trust_level="low",
        commit_sha="abc123",
    )

    assert source.security_flags
    assert "should-not-appear" not in source.spans[0].preview
    assert "[REDACTED]" in source.spans[0].preview
