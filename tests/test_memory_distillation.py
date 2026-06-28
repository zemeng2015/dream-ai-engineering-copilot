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
    assert scan.schema_version == "memory-scan-v0.2"
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
    candidate = next(claim for claim in scan.claims if claim.governance.status == "candidate")

    event = service.review_claim(
        team_id="demo_team",
        claim_id=candidate.claim_id,
        new_status="approved",
        reviewer="zack",
        reason="Validated source-backed candidate.",
        scan_id=scan.scan_id,
    )
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

    assert event.previous_status == "candidate"
    assert repository.ledger_path("demo_team").exists()
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
