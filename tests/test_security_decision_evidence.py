# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from dream.core.errors import (
    AccessDeniedError,
    DreamError,
    SecurityEvidenceUnavailableError,
)
from dream.security import AccessContext, DefaultAccessPolicy, RequestPrincipal, ResourceAccess
from dream.security.evidence import SecurityDecisionRepository, hash_evidence_value
from dream.security.identity import SignedProxyIdentityProvider
from dream.security.revocation import AccessRevocationRegistry

SECRET = "test-only-identity-secret-with-at-least-32-bytes"
NOW = 1_800_000_000


def _headers(**overrides: str) -> dict[str, str]:
    headers = {
        "x-dream-principal-id": "private-user-123",
        "x-dream-team-ids": "team-a",
        "x-dream-group-ids": "engineering-a",
        "x-dream-roles": "viewer",
        "x-dream-identity-timestamp": str(NOW),
        "x-request-id": "private-request-42",
    }
    headers.update(overrides)
    headers["x-dream-identity-signature"] = SignedProxyIdentityProvider.signature_for(
        secret=SECRET,
        principal_id=headers["x-dream-principal-id"],
        team_ids={item for item in headers["x-dream-team-ids"].split(",") if item},
        group_ids={item for item in headers["x-dream-group-ids"].split(",") if item},
        roles={item for item in headers["x-dream-roles"].split(",") if item},
        timestamp=int(headers["x-dream-identity-timestamp"]),
        request_id=headers["x-request-id"],
        method="GET",
        path="/private/resource",
    )
    return headers


def _context() -> AccessContext:
    return AccessContext(
        mode="private-extension",
        principal=RequestPrincipal(
            principal_id="private-user-123",
            authenticated=True,
            team_ids={"team-a"},
            group_ids={"engineering-a"},
            roles={"viewer"},
        ),
        request_id="private-request-42",
    )


def _access() -> ResourceAccess:
    return ResourceAccess(
        classification="internal",
        acl_scope="source_acl",
        allowed_group_ids={"engineering-a"},
        source_acl_version="acl-private-v1",
    )


def test_identity_decisions_persist_trusted_success_and_unattributed_denial(
    tmp_path: Path,
) -> None:
    repository = SecurityDecisionRepository(tmp_path / "artifacts")
    provider = SignedProxyIdentityProvider(
        secret=SECRET,
        decision_repository=repository,
    )

    provider.authenticate(
        _headers(),
        method="GET",
        path="/private/resource",
        now=NOW,
    )
    tampered = _headers()
    tampered["x-dream-team-ids"] = "forged-secret-team"
    with pytest.raises(AccessDeniedError, match="signature"):
        provider.authenticate(
            tampered,
            method="GET",
            path="/private/resource",
            now=NOW,
        )

    events = repository.load_identity()
    assert [item.status for item in events] == ["allowed", "blocked"]
    assert events[0].team_id_hashes == [hash_evidence_value("team-a")]
    assert events[0].principal_id_hash == hash_evidence_value("private-user-123")
    assert events[1].reason_code == "signature_invalid"
    assert events[1].team_id_hashes == []
    assert events[1].principal_id_hash is None
    payload = repository.identity_path.read_text(encoding="utf-8")
    assert "private-user-123" not in payload
    assert "private-request-42" not in payload
    assert "team-a" not in payload
    assert "forged-secret-team" not in payload
    assert "/private/resource" not in payload


def test_access_policy_persists_allow_and_deny_without_raw_identifiers(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    repository = SecurityDecisionRepository(artifacts)
    policy = DefaultAccessPolicy(
        revocation_registry=AccessRevocationRegistry(
            artifacts / "pilot-security/access-revocations.json"
        ),
        decision_repository=repository,
    )

    assert policy.decide(
        context=_context(),
        team_id="team-a",
        action="retrieve",
        resource_access=_access(),
        resource_id="private-resource-1",
    ).allowed
    assert not policy.decide(
        context=_context(),
        team_id="team-b",
        action="retrieve",
        resource_access=_access(),
        resource_id="other-resource-2",
    ).allowed

    events = repository.load_access()
    assert [(item.allowed, item.reason_code) for item in events] == [
        (True, "source_acl_allowed"),
        (False, "team_not_authorized"),
    ]
    assert events[0].team_id_hash == hash_evidence_value("team-a")
    assert events[0].classification == "internal"
    assert events[0].acl_scope == "source_acl"
    assert events[0].source_acl_version_hashes == [
        hash_evidence_value("acl-private-v1")
    ]
    assert events[1].team_id_hash == hash_evidence_value("team-b")
    payload = repository.access_path.read_text(encoding="utf-8")
    for value in (
        "private-user-123",
        "private-request-42",
        "team-a",
        "team-b",
        "private-resource-1",
        "other-resource-2",
    ):
        assert value not in payload


def test_security_decision_persistence_failure_denies_runtime_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SecurityDecisionRepository(tmp_path / "artifacts")

    def fail_identity(_evidence) -> None:
        raise DreamError("private disk detail")

    monkeypatch.setattr(repository, "record_identity", fail_identity)
    provider = SignedProxyIdentityProvider(
        secret=SECRET,
        decision_repository=repository,
    )
    with pytest.raises(
        SecurityEvidenceUnavailableError,
        match="evidence is unavailable",
    ) as exc:
        provider.authenticate(
            _headers(),
            method="GET",
            path="/private/resource",
            now=NOW,
        )
    assert "private disk detail" not in str(exc.value)

    def fail_access(_evidence) -> None:
        raise DreamError("private disk detail")

    monkeypatch.setattr(repository, "record_access", fail_access)
    policy = DefaultAccessPolicy(
        revocation_registry=AccessRevocationRegistry(
            tmp_path / "artifacts/pilot-security/access-revocations.json"
        ),
        decision_repository=repository,
    )
    with pytest.raises(AccessDeniedError, match="evidence is unavailable") as exc:
        policy.decide(
            context=_context(),
            team_id="team-a",
            action="retrieve",
            resource_access=_access(),
        )
    assert "private disk detail" not in str(exc.value)
