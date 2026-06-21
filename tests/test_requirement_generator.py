# SPDX-License-Identifier: Apache-2.0

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.requirements import RequirementDraftGenerator, RequirementDraftRequest


def test_requirement_draft_generation_with_mock_provider(tmp_path) -> None:
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    generator = RequirementDraftGenerator(audit_logger=audit_logger)

    response = generator.draft(
        RequirementDraftRequest(
            team_id="demo_team",
            rough_business_request="Add async status tracking for long-running job execution",
        )
    )

    assert response.run_id.startswith("req-")
    assert "# Requirement Draft" in response.markdown
    assert "This is a draft for human review." in response.markdown
    assert response.sources_used
    assert audit_logger.repository.get_audit_record(response.run_id) is not None

