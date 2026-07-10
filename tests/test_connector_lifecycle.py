# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from dream.codebase.models import FileNode, RepoIndex
from dream.codebase.repository import CodebaseIndexRepository
from dream.connectors import (
    ArtifactLineageRegistry,
    ConnectorLifecycleRepository,
    ConnectorLifecycleService,
    ConnectorSourceSnapshot,
)
from dream.connectors.models import connector_source_key
from dream.context.models import PromptPreview
from dream.context.repository import ContextArtifactRepository
from dream.core.errors import AccessDeniedError, NotFoundError, PathTraversalError
from dream.graph.models import EvidenceGraph, EvidenceNode
from dream.graph.repository import EvidenceGraphRepository
from dream.memory.models import MemoryScanResult, MemoryValidationSummary, SourceRecord
from dream.memory.repository import MemoryDistillationRepository
from dream.requirement_cases.models import (
    ContextEvidence,
    RequirementCase,
    RequirementCaseSnapshot,
)
from dream.requirement_cases.repository import RequirementCaseRepository
from dream.security import AccessContext, RequestPrincipal, ResourceAccess
from dream.security.policy import DefaultAccessPolicy
from dream.security.revocation import AccessRevocationRegistry

TEAM_ID = "team-a"
CONNECTOR_ID = "github-enterprise"
SOURCE_ID = "repo/platform/docs/status.md"


def _context(*, roles: set[str] | None = None) -> AccessContext:
    return AccessContext(
        mode="private-extension",
        principal=RequestPrincipal(
            principal_id="connector-service",
            authenticated=True,
            team_ids={TEAM_ID},
            group_ids={"engineering-a"},
            roles=roles or {"source_admin"},
        ),
    )


def _access(version: str) -> ResourceAccess:
    return ResourceAccess(
        classification="internal",
        acl_scope="source_acl",
        allowed_group_ids={"engineering-a"},
        source_acl_version=version,
    )


def _derived_access(version: str) -> ResourceAccess:
    return ResourceAccess(
        classification="internal",
        acl_scope="source_acl",
        allowed_principal_ids={"connector-service"},
        source_acl_version=f"derived:{version}",
        source_acl_lineage={version},
    )


def _snapshot(
    *,
    source_version: str = "source-v1",
    previous_source_version: str | None = None,
    content_hash: str = "sha256:content-v1",
    acl_version: str = "acl-v1",
) -> ConnectorSourceSnapshot:
    return ConnectorSourceSnapshot(
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
        team_id=TEAM_ID,
        source_type="document",
        source_version=source_version,
        previous_source_version=previous_source_version,
        content_hash=content_hash,
        access=_access(acl_version),
        observed_at="2026-07-10T12:00:00+00:00",
    )


def _service(
    artifacts_dir: Path,
    requirement_repository: RequirementCaseRepository,
    registry: ArtifactLineageRegistry,
) -> ConnectorLifecycleService:
    return ConnectorLifecycleService(
        artifacts_dir=artifacts_dir,
        lifecycle_repository=ConnectorLifecycleRepository(artifacts_dir),
        lineage_registry=registry,
        revocation_registry=AccessRevocationRegistry(
            artifacts_dir / "pilot-security/access-revocations.json"
        ),
        requirement_repository=requirement_repository,
    )


def test_connector_sync_requires_private_source_admin_and_immutable_versions(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    registry = ArtifactLineageRegistry(artifacts)
    cases = RequirementCaseRepository(tmp_path / "cases.sqlite", lineage_registry=registry)
    service = _service(artifacts, cases, registry)

    assert connector_source_key(team_id="a:b", connector_id="c", source_id="d") != (
        connector_source_key(team_id="a", connector_id="b:c", source_id="d")
    )

    with pytest.raises(AccessDeniedError, match="source administrator"):
        service.sync_source(_snapshot(), access_context=_context(roles={"viewer"}))

    activated = service.sync_source(_snapshot(), access_context=_context())
    unchanged = service.sync_source(_snapshot(), access_context=_context())

    assert activated.action == "activated"
    assert unchanged.action == "unchanged"
    assert unchanged.revoked_acl_versions == set()

    with pytest.raises(NotFoundError, match="existing file"):
        service.register_source_copy(
            team_id=TEAM_ID,
            connector_id=CONNECTOR_ID,
            source_id=SOURCE_ID,
            path=artifacts / "missing-source-copy.md",
            access_context=_context(),
        )

    with pytest.raises(ValueError, match="new source version"):
        service.sync_source(
            _snapshot(
                previous_source_version="source-v1",
                content_hash="sha256:changed",
                acl_version="acl-v2",
            ),
            access_context=_context(),
        )
    with pytest.raises(ValueError, match="new ACL version"):
        service.sync_source(
            _snapshot(
                source_version="source-v2",
                previous_source_version="source-v1",
                content_hash="sha256:changed",
            ),
            access_context=_context(),
        )

    with pytest.raises(ValueError, match="stale"):
        service.sync_source(
            _snapshot(
                source_version="source-v3",
                previous_source_version="source-v0",
                content_hash="sha256:content-v3",
                acl_version="acl-v3",
            ),
            access_context=_context(),
        )


def test_acl_refresh_revokes_old_version_and_purges_all_registered_derivations(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    registry = ArtifactLineageRegistry(artifacts)
    cases = RequirementCaseRepository(tmp_path / "cases.sqlite", lineage_registry=registry)
    service = _service(artifacts, cases, registry)
    service.sync_source(_snapshot(), access_context=_context())
    access = _access("acl-v1")
    derived_access = _derived_access("acl-v1")

    source_copy = artifacts / "connector-sources/source-copy.md"
    source_copy.parent.mkdir(parents=True)
    source_copy.write_text("private source body", encoding="utf-8")
    service.register_source_copy(
        team_id=TEAM_ID,
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
        path=source_copy,
        access_context=_context(),
    )

    codebase_repository = CodebaseIndexRepository(artifacts, lineage_registry=registry)
    codebase_repository.save(
        RepoIndex(
            repo_id="repo-a",
            repo_name="repo-a",
            repo_path="private/repo-a",
            team_id=TEAM_ID,
            indexed_at="2026-07-10T12:00:00+00:00",
            files=[
                FileNode(
                    file_id="file-a",
                    path="private/status.py",
                    language="python",
                    size_bytes=20,
                    line_count=1,
                    role="source",
                    access=access,
                )
            ],
            summary="Private codebase index",
            access=ResourceAccess.unscoped_private(),
        )
    )
    graph_repository = EvidenceGraphRepository(artifacts, lineage_registry=registry)
    graph_repository.save(
        EvidenceGraph(
            graph_id="graph-a",
            team_id=TEAM_ID,
            repo_name="repo-a",
            built_at="2026-07-10T12:00:00+00:00",
            nodes=[
                EvidenceNode(
                    node_id="doc:status",
                    node_type="document",
                    key="status",
                    title="Status",
                    source_path="private/status.md",
                    access=access,
                )
            ],
            summary="Private evidence graph",
        )
    )
    memory_repository = MemoryDistillationRepository(artifacts, lineage_registry=registry)
    memory_repository.save_scan(
        MemoryScanResult(
            scan_id="scan-a",
            team_id=TEAM_ID,
            repo_name="repo-a",
            created_at="2026-07-10T12:00:00+00:00",
            sources=[
                SourceRecord(
                    source_id="source-a",
                    source_type="document",
                    team_id=TEAM_ID,
                    path="private/status.md",
                    content_hash="sha256:content-v1",
                    indexed_at="2026-07-10T12:00:00+00:00",
                    access=access,
                )
            ],
            validation=MemoryValidationSummary(
                citation_validity=1.0,
                unsupported_claim_rate=0.0,
                secret_leakage_count=0,
                structural_claims=0,
                semantic_candidate_claims=0,
                auto_promoted_semantic_claims=0,
            ),
            summary="Private memory scan",
        )
    )
    context_repository = ContextArtifactRepository(artifacts, lineage_registry=registry)
    preview = context_repository.save_prompt_preview(
        PromptPreview(
            preview_id="preview-a",
            team_id=TEAM_ID,
            target="jira_draft",
            provider_mode="approved-enterprise",
            prompt_text="private prompt body",
            evidence_paths=["private/status.md"],
            access=derived_access,
        )
    )
    cases.save(
        RequirementCaseSnapshot(
            case=RequirementCase(
                case_id="case-a",
                team_id=TEAM_ID,
                title="Private case",
                raw_request="Private request",
                status="analyzed",
                created_at="2026-07-10T12:00:00+00:00",
                updated_at="2026-07-10T12:00:00+00:00",
                access=ResourceAccess.unscoped_private(),
            ),
            evidence=[
                ContextEvidence(
                    evidence_id="evidence-a",
                    case_id="case-a",
                    source_type="document",
                    source_path="private/status.md",
                    title="Private status source",
                    excerpt="private excerpt",
                    relevance_score=1.0,
                    reason="Exact match",
                    access=access,
                )
            ],
        )
    )

    refreshed = service.sync_source(
        _snapshot(
            source_version="source-v2",
            previous_source_version="source-v1",
            content_hash="sha256:content-v2",
            acl_version="acl-v2",
        ),
        access_context=_context(),
    )

    assert refreshed.action == "replaced"
    assert refreshed.revoked_acl_versions == {"acl-v1"}
    assert refreshed.purge_report.cleanup_complete
    assert len(refreshed.purge_report.items) == 7
    assert not source_copy.exists()
    assert codebase_repository.try_load(TEAM_ID, "repo-a") is None
    assert graph_repository.try_load(TEAM_ID, "repo-a") is None
    assert not memory_repository.scan_path(TEAM_ID, "scan-a").exists()
    assert not memory_repository.latest_scan_path(TEAM_ID).exists()
    assert not Path(preview.json_path or "missing").exists()
    with pytest.raises(NotFoundError):
        cases.get("case-a")

    stale_decision = DefaultAccessPolicy(revocation_registry=service.revocation_registry).decide(
        context=_context(roles={"viewer"}),
        team_id=TEAM_ID,
        action="retrieve",
        resource_access=derived_access,
        resource_id="stale-in-memory-artifact",
    )
    assert not stale_decision.allowed
    assert stale_decision.reason_code == "source_acl_revoked"


def test_connector_delete_tombstones_source_and_survives_service_restart(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    registry = ArtifactLineageRegistry(artifacts)
    cases = RequirementCaseRepository(tmp_path / "cases.sqlite", lineage_registry=registry)
    service = _service(artifacts, cases, registry)
    service.sync_source(_snapshot(), access_context=_context())
    source_copy = artifacts / "connector-sources/delete-me.md"
    source_copy.parent.mkdir(parents=True)
    source_copy.write_text("delete me", encoding="utf-8")
    service.register_source_copy(
        team_id=TEAM_ID,
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
        path=source_copy,
        access_context=_context(),
    )

    with pytest.raises(ValueError, match="version changed"):
        service.delete_source(
            team_id=TEAM_ID,
            connector_id=CONNECTOR_ID,
            source_id=SOURCE_ID,
            expected_source_version="stale-version",
            reason="Source owner removed access.",
            access_context=_context(),
        )
    assert source_copy.exists()

    deleted = service.delete_source(
        team_id=TEAM_ID,
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
        expected_source_version="source-v1",
        reason="Source owner removed access.",
        access_context=_context(),
    )

    assert deleted.action == "deleted"
    assert deleted.source.status == "deleted"
    assert deleted.source.deleted_by == "connector-service"
    assert deleted.purge_report.cleanup_complete
    assert not source_copy.exists()

    restarted = _service(
        artifacts,
        RequirementCaseRepository(tmp_path / "cases.sqlite", lineage_registry=registry),
        ArtifactLineageRegistry(artifacts),
    )
    persisted = restarted.lifecycle_repository.get(
        team_id=TEAM_ID,
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
    )
    assert persisted.status == "deleted"
    assert restarted.revocation_registry.is_revoked(
        team_id=TEAM_ID,
        acl_versions={"acl-v1"},
    )
    with pytest.raises(AccessDeniedError, match="source_acl_revoked"):
        restarted.sync_source(_snapshot(), access_context=_context())


def test_connector_delete_still_cleans_up_after_security_revoked_source(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    registry = ArtifactLineageRegistry(artifacts)
    cases = RequirementCaseRepository(tmp_path / "cases.sqlite", lineage_registry=registry)
    service = _service(artifacts, cases, registry)
    service.sync_source(_snapshot(), access_context=_context())
    source_copy = artifacts / "connector-sources/revoked-before-delete.md"
    source_copy.parent.mkdir(parents=True)
    source_copy.write_text("revoked private body", encoding="utf-8")
    service.register_source_copy(
        team_id=TEAM_ID,
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
        path=source_copy,
        access_context=_context(),
    )
    service.revocation_registry.revoke(
        team_id=TEAM_ID,
        source_acl_version="acl-v1",
        revoked_by="security-admin",
        reason="Emergency access removal.",
    )

    deleted = service.delete_source(
        team_id=TEAM_ID,
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
        expected_source_version="source-v1",
        reason="Connector confirmed source deletion.",
        access_context=_context(),
    )

    assert deleted.action == "deleted"
    assert deleted.purge_report.cleanup_complete
    assert not source_copy.exists()


def test_lineage_registry_rejects_paths_outside_artifact_root(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    registry = ArtifactLineageRegistry(artifacts)

    with pytest.raises(PathTraversalError):
        registry.register_path(
            team_id=TEAM_ID,
            artifact_kind="unsafe",
            path=tmp_path / "outside.txt",
            access=_access("acl-v1"),
        )
    with pytest.raises(PathTraversalError):
        registry.register_path(
            team_id=TEAM_ID,
            artifact_kind="unsafe",
            path=artifacts,
            access=_access("acl-v1"),
            directory=True,
        )
    control_file = artifacts / "pilot-security/unsafe-source-copy.md"
    control_file.parent.mkdir(parents=True)
    control_file.write_text("must not be registered", encoding="utf-8")
    with pytest.raises(PathTraversalError, match="control-plane"):
        registry.register_path(
            team_id=TEAM_ID,
            artifact_kind="unsafe",
            path=control_file,
            access=_access("acl-v1"),
        )


def test_cleanup_failure_remains_visible_for_operator_retry(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    registry = ArtifactLineageRegistry(artifacts)
    registry.register_requirement_case(
        team_id=TEAM_ID,
        case_id="case-without-cleanup-handler",
        access=_derived_access("acl-v1"),
    )

    report = registry.purge(
        team_id=TEAM_ID,
        acl_versions={"acl-v1"},
        reason="Connector source deleted.",
    )

    assert not report.cleanup_complete
    assert report.items[0].status == "cleanup_failed"
    assert "handler is not configured" in (report.items[0].error or "")
    record = registry.load().records[0]
    assert record.status == "cleanup_failed"
    assert record.cleanup_error


def test_tombstoned_source_cleanup_can_be_retried_without_restoring_access(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    registry = ArtifactLineageRegistry(artifacts)
    cases = RequirementCaseRepository(tmp_path / "cases.sqlite", lineage_registry=registry)
    service = _service(artifacts, cases, registry)
    service.sync_source(_snapshot(), access_context=_context())
    mismatched = artifacts / "derived/mismatched-artifact"
    mismatched.mkdir(parents=True)
    registry.register_path(
        team_id=TEAM_ID,
        artifact_kind="mismatched_test_artifact",
        path=mismatched,
        access=_access("acl-v1"),
        directory=False,
    )

    deleted = service.delete_source(
        team_id=TEAM_ID,
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
        expected_source_version="source-v1",
        reason="Source deleted; initial cleanup should expose mismatch.",
        access_context=_context(),
    )
    assert not deleted.purge_report.cleanup_complete
    assert deleted.source.status == "deleted"

    mismatched.rmdir()
    mismatched.write_text("corrected artifact locator", encoding="utf-8")
    retried = service.retry_cleanup(
        team_id=TEAM_ID,
        connector_id=CONNECTOR_ID,
        source_id=SOURCE_ID,
        reason="Operator corrected the artifact locator type.",
        access_context=_context(),
    )

    assert retried.action == "cleanup_retry"
    assert retried.source.status == "deleted"
    assert retried.purge_report.cleanup_complete
    assert not mismatched.exists()
    assert service.revocation_registry.is_revoked(
        team_id=TEAM_ID,
        acl_versions={"acl-v1"},
    )
