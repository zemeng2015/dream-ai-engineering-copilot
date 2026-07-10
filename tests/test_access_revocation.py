# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from dream.core.errors import DreamError
from dream.security import (
    AccessContext,
    AccessRevocationRegistry,
    DefaultAccessPolicy,
    RequestPrincipal,
    ResourceAccess,
)


def _context(team_id: str = "team-a") -> AccessContext:
    return AccessContext(
        mode="private-extension",
        principal=RequestPrincipal(
            principal_id="user-123",
            authenticated=True,
            team_ids={team_id},
            group_ids={"engineering-a"},
            roles={"viewer"},
        ),
    )


def _access(version: str) -> ResourceAccess:
    return ResourceAccess(
        classification="internal",
        acl_scope="source_acl",
        allowed_group_ids={"engineering-a"},
        source_acl_version=version,
    )


def test_revoked_source_acl_invalidates_source_and_derived_artifact(tmp_path: Path) -> None:
    registry = AccessRevocationRegistry(tmp_path / "revocations.json")
    policy = DefaultAccessPolicy(revocation_registry=registry)
    context = _context()
    source = _access("source-v7")
    requested = _access("case-v2")
    derived = policy.derive_artifact_access(
        context=context,
        team_id="team-a",
        source_access=[source],
        requested_access=requested,
    )

    assert policy.decide(
        context=context,
        team_id="team-a",
        action="retrieve",
        resource_access=source,
    ).allowed
    assert policy.decide(
        context=context,
        team_id="team-a",
        action="retrieve",
        resource_access=derived,
    ).allowed
    assert derived.source_acl_lineage == {"source-v7", "case-v2"}

    registry.revoke(
        team_id="team-a",
        source_acl_version="source-v7",
        revoked_by="source-owner-1",
        reason="Caller access was removed in the source system.",
        revoked_at="2026-07-10T00:00:00Z",
    )

    source_decision = policy.decide(
        context=context,
        team_id="team-a",
        action="retrieve",
        resource_access=source,
    )
    derived_decision = policy.decide(
        context=context,
        team_id="team-a",
        action="retrieve",
        resource_access=derived,
    )
    assert not source_decision.allowed
    assert source_decision.reason_code == "source_acl_revoked"
    assert not derived_decision.allowed
    assert derived_decision.reason_code == "source_acl_revoked"


def test_revocation_is_team_scoped_and_idempotent(tmp_path: Path) -> None:
    registry = AccessRevocationRegistry(tmp_path / "revocations.json")
    for _ in range(2):
        registry.revoke(
            team_id="team-a",
            source_acl_version="shared-version",
            revoked_by="source-owner-1",
            reason="test revocation",
            revoked_at="2026-07-10T00:00:00Z",
        )

    assert registry.is_revoked(team_id="team-a", acl_versions={"shared-version"})
    assert not registry.is_revoked(team_id="team-b", acl_versions={"shared-version"})
    assert len(registry.load().events) == 1


def test_invalid_revocation_ledger_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "revocations.json"
    path.write_text("not-json", encoding="utf-8")
    policy = DefaultAccessPolicy(
        revocation_registry=AccessRevocationRegistry(path),
    )

    with pytest.raises(DreamError, match="revocation ledger"):
        policy.decide(
            context=_context(),
            team_id="team-a",
            action="retrieve",
            resource_access=_access("source-v1"),
        )
