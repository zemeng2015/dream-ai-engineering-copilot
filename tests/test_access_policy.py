# SPDX-License-Identifier: Apache-2.0

import pytest

from dream.core.errors import AccessDeniedError
from dream.security import (
    AccessContext,
    DefaultAccessPolicy,
    RequestPrincipal,
    ResourceAccess,
)


def _private_context(
    *,
    principal_id: str = "user-123",
    authenticated: bool = True,
    team_ids: set[str] | None = None,
    group_ids: set[str] | None = None,
    roles: set[str] | None = None,
) -> AccessContext:
    return AccessContext(
        mode="private-extension",
        principal=RequestPrincipal(
            principal_id=principal_id,
            authenticated=authenticated,
            team_ids=team_ids or {"team-a"},
            group_ids=group_ids or {"engineering-a"},
            roles=roles or {"viewer"},
        ),
    )


def _source_acl(**overrides: object) -> ResourceAccess:
    payload: dict[str, object] = {
        "classification": "internal",
        "acl_scope": "source_acl",
        "allowed_group_ids": {"engineering-a"},
        "source_acl_version": "etag-42",
    }
    payload.update(overrides)
    return ResourceAccess.model_validate(payload)


def test_public_demo_allows_only_local_public_demo_resources() -> None:
    policy = DefaultAccessPolicy()
    context = AccessContext.public_demo(team_ids={"demo_team"})

    assert policy.decide(
        context=context,
        team_id="demo_team",
        action="retrieve",
        resource_access=ResourceAccess(),
    ).allowed
    assert not policy.decide(
        context=context,
        team_id="demo_team",
        action="retrieve",
        resource_access=_source_acl(),
    ).allowed
    assert not policy.decide(
        context=context,
        team_id="other-team",
        action="retrieve",
        resource_access=ResourceAccess(),
    ).allowed


@pytest.mark.parametrize(
    ("context", "resource_access", "reason"),
    [
        (_private_context(authenticated=False), _source_acl(), "principal_not_authenticated"),
        (_private_context(team_ids={"team-b"}), _source_acl(), "team_not_authorized"),
        (_private_context(roles={"source_admin"}), _source_acl(), "role_not_authorized"),
        (_private_context(), None, "resource_acl_missing"),
        (_private_context(), ResourceAccess.unscoped_private(), "source_acl_unscoped"),
        (
            _private_context(),
            _source_acl(source_acl_version=None),
            "source_acl_version_missing",
        ),
        (
            _private_context(group_ids={"other-group"}),
            _source_acl(),
            "source_acl_denied",
        ),
        (
            _private_context(),
            _source_acl(classification="blocked"),
            "classification_blocked",
        ),
    ],
)
def test_private_policy_fails_closed(
    context: AccessContext,
    resource_access: ResourceAccess | None,
    reason: str,
) -> None:
    decision = DefaultAccessPolicy().decide(
        context=context,
        team_id="team-a",
        action="retrieve",
        resource_access=resource_access,
        resource_id="doc-1",
    )

    assert not decision.allowed
    assert decision.reason_code == reason
    assert decision.resource_id == "doc-1"


def test_private_policy_requires_source_acl_match_even_for_security_admin() -> None:
    context = _private_context(
        group_ids={"other-group"},
        roles={"security_admin"},
    )

    decision = DefaultAccessPolicy().decide(
        context=context,
        team_id="team-a",
        action="retrieve",
        resource_access=_source_acl(),
    )

    assert not decision.allowed
    assert decision.reason_code == "source_acl_denied"


def test_private_policy_allows_principal_or_group_acl_match() -> None:
    policy = DefaultAccessPolicy()
    context = _private_context()

    group_decision = policy.decide(
        context=context,
        team_id="team-a",
        action="retrieve",
        resource_access=_source_acl(),
    )
    principal_decision = policy.decide(
        context=context,
        team_id="team-a",
        action="retrieve",
        resource_access=_source_acl(
            allowed_group_ids=set(),
            allowed_principal_ids={"user-123"},
        ),
    )

    assert group_decision.allowed
    assert principal_decision.allowed


def test_private_action_roles_are_independent_from_source_acl() -> None:
    policy = DefaultAccessPolicy()
    reviewer = _private_context(roles={"memory_reviewer"})
    viewer = _private_context(roles={"viewer"})

    assert policy.decide(
        context=reviewer,
        team_id="team-a",
        action="memory_review",
        resource_access=_source_acl(),
    ).allowed
    assert not policy.decide(
        context=viewer,
        team_id="team-a",
        action="memory_review",
        resource_access=_source_acl(),
    ).allowed


def test_require_raises_without_exposing_resource_content() -> None:
    with pytest.raises(AccessDeniedError, match="source_acl_denied") as exc_info:
        DefaultAccessPolicy().require(
            context=_private_context(group_ids={"other-group"}),
            team_id="team-a",
            action="retrieve",
            resource_access=_source_acl(),
            resource_id="safe-resource-id",
        )

    assert "safe-resource-id" not in str(exc_info.value)


def test_derived_artifact_acl_never_broadens_source_access() -> None:
    context = _private_context(group_ids={"engineering-a", "engineering-b"})
    requested = _source_acl(
        allowed_group_ids={"engineering-a", "engineering-b"},
        source_acl_version="case-v1",
    )
    source = _source_acl(
        allowed_group_ids={"engineering-a"},
        source_acl_version="source-v7",
    )

    derived = DefaultAccessPolicy().derive_artifact_access(
        context=context,
        team_id="team-a",
        source_access=[source],
        requested_access=requested,
    )

    assert derived.allowed_group_ids == {"engineering-a"}
    assert derived.allowed_principal_ids == {"user-123"}
    assert derived.source_acl_version.startswith("derived:")
    assert (
        not DefaultAccessPolicy()
        .decide(
            context=_private_context(
                principal_id="user-b",
                group_ids={"engineering-b"},
            ),
            team_id="team-a",
            action="retrieve",
            resource_access=derived,
        )
        .allowed
    )
