# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase.repository import CodebaseIndexRepository
from dream.graph.repository import EvidenceGraphRepository
from dream.knowledge import KnowledgePackLoader, MarkdownDocumentLoader
from dream.memory import EngineeringMemoryRetriever, MemoryClaimRetriever
from dream.memory.repository import MemoryDistillationRepository
from dream.requirement_cases import RequirementCaseCreateRequest, RequirementCaseService
from dream.requirement_cases.repository import RequirementCaseRepository
from dream.security import AccessContext, RequestPrincipal, ResourceAccess


def _private_context() -> AccessContext:
    return AccessContext(
        mode="private-extension",
        principal=RequestPrincipal(
            principal_id="user-123",
            authenticated=True,
            team_ids={"team-a"},
            group_ids={"engineering-a"},
            roles={"viewer", "author"},
        ),
    )


def _access(group_id: str) -> ResourceAccess:
    return ResourceAccess(
        classification="internal",
        acl_scope="source_acl",
        allowed_group_ids={group_id},
        source_acl_version=f"acl-{group_id}-v1",
    )


def _write_pack(root: Path) -> None:
    pack_dir = root / "team-a"
    docs_dir = pack_dir / "docs"
    docs_dir.mkdir(parents=True)
    (pack_dir / "team.yaml").write_text(
        "\n".join(
            [
                "team_name: Team A",
                "team_id: team-a",
                "document_paths:",
                "  - docs",
            ]
        ),
        encoding="utf-8",
    )
    (docs_dir / "allowed-status.md").write_text(
        """---
doc_type: architecture
classification: internal
acl_scope: source_acl
allowed_group_ids:
  - engineering-a
source_acl_version: allowed-v1
---
# Allowed Status Architecture

The status tracker persists allowed lifecycle transitions.
""",
        encoding="utf-8",
    )
    (docs_dir / "restricted-status.md").write_text(
        """---
doc_type: incident
classification: sensitive
acl_scope: source_acl
allowed_group_ids:
  - engineering-b
source_acl_version: restricted-v1
---
# Restricted Status Incident

FORBIDDEN-DETAIL status tracker customer incident.
""",
        encoding="utf-8",
    )


def test_private_requirement_prompt_and_trail_exclude_denied_sources(
    monkeypatch,
    tmp_path: Path,
) -> None:
    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(artifacts_dir))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(tmp_path / "audit.sqlite"))
    packs_dir = tmp_path / "packs"
    _write_pack(packs_dir)

    pack_loader = KnowledgePackLoader(packs_dir=packs_dir)
    codebase_repository = CodebaseIndexRepository(artifacts_dir)
    graph_repository = EvidenceGraphRepository(artifacts_dir)
    memory_repository = MemoryDistillationRepository(artifacts_dir)
    requirement_repository = RequirementCaseRepository(tmp_path / "cases.sqlite")
    retriever = EngineeringMemoryRetriever(
        pack_loader=pack_loader,
        doc_loader=MarkdownDocumentLoader(),
        codebase_repository=codebase_repository,
        graph_repository=graph_repository,
    )
    service = RequirementCaseService(
        repository=requirement_repository,
        memory_retriever=retriever,
        memory_claim_retriever=MemoryClaimRetriever(repository=memory_repository),
        codebase_repository=codebase_repository,
        audit_logger=AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite")),
    )
    context = _private_context()
    created = service.create_case(
        RequirementCaseCreateRequest(
            team_id="team-a",
            raw_request="Improve status tracker lifecycle visibility.",
            access=ResourceAccess(
                classification="internal",
                acl_scope="source_acl",
                allowed_group_ids={"engineering-a", "engineering-b"},
                source_acl_version="case-request-v1",
            ),
        ),
        case_id="case-private-acl",
        access_context=context,
    )

    analyzed = service.analyze_case(
        created.case.case_id,
        access_context=context,
    )
    jira = service.generate_jira_draft(
        created.case.case_id,
        access_context=context,
    )

    evidence_text = "\n".join(
        f"{item.source_path}\n{item.title}\n{item.excerpt}" for item in analyzed.evidence
    )
    assert "allowed-status.md" in evidence_text
    assert "restricted-status.md" not in evidence_text
    assert "FORBIDDEN-DETAIL" not in evidence_text
    assert analyzed.case.access.allowed_group_ids == {"engineering-a"}
    assert analyzed.case.access.allowed_principal_ids == {"user-123"}
    assert analyzed.case.access.source_acl_version.startswith("derived:")
    assert "restricted-status.md" not in jira.markdown
    assert "FORBIDDEN-DETAIL" not in jira.markdown

    from dream.context import ContextIntelligenceService

    context_service = ContextIntelligenceService(
        requirement_repository=requirement_repository,
        graph_repository=graph_repository,
        memory_repository=memory_repository,
        codebase_repository=codebase_repository,
    )
    trail = context_service.trace_case(
        created.case.case_id,
        access_context=context,
    )
    preview = context_service.prompt_for_case(
        created.case.case_id,
        access_context=context,
    )
    serialized_trust_output = "\n".join(
        [
            trail.model_dump_json(),
            preview.model_dump_json(),
        ]
    )
    assert "restricted-status.md" not in serialized_trust_output
    assert "FORBIDDEN-DETAIL" not in serialized_trust_output
