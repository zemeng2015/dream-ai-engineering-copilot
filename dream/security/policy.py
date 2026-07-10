# SPDX-License-Identifier: Apache-2.0

import hashlib
from collections.abc import Callable, Iterable
from typing import TypeVar

from dream.core.errors import AccessDeniedError
from dream.security.models import (
    AccessAction,
    AccessContext,
    AccessDecision,
    ResourceAccess,
)
from dream.security.revocation import AccessRevocationRegistry

_ACTION_ROLES: dict[AccessAction, set[str]] = {
    "retrieve": {"viewer", "author", "memory_reviewer", "auditor", "security_admin"},
    "source_intake": {"source_admin", "security_admin"},
    "memory_review": {"memory_reviewer", "security_admin"},
    "requirement_work": {"author", "memory_reviewer", "security_admin"},
    "audit_read": {"auditor", "security_admin"},
    "security_admin": {"security_admin"},
}

T = TypeVar("T")


class DefaultAccessPolicy:
    """Fail-closed source authorization for the private Pilot boundary.

    `public-demo` intentionally supports only synthetic `public_demo` resources.
    `private-extension` requires an authenticated named principal, explicit team
    membership, an allowed action role, and versioned source ACL metadata that
    matches the principal or one of their groups.
    """

    policy_name = "default-access-policy-v1"

    def __init__(
        self,
        *,
        revocation_registry: AccessRevocationRegistry | None = None,
    ) -> None:
        self.revocation_registry = revocation_registry or AccessRevocationRegistry()

    def decide(
        self,
        *,
        context: AccessContext,
        team_id: str,
        action: AccessAction,
        resource_access: ResourceAccess | None = None,
        resource_id: str | None = None,
    ) -> AccessDecision:
        principal = context.principal

        if not principal.authenticated:
            return self._decision(
                False, "principal_not_authenticated", context, team_id, action, resource_id
            )
        if not self._team_allowed(context=context, team_id=team_id):
            return self._decision(
                False, "team_not_authorized", context, team_id, action, resource_id
            )

        if context.mode == "private-extension" and not (principal.roles & _ACTION_ROLES[action]):
            return self._decision(
                False, "role_not_authorized", context, team_id, action, resource_id
            )

        if resource_access is None:
            return self._decision(
                False, "resource_acl_missing", context, team_id, action, resource_id
            )
        if resource_access.classification == "blocked":
            return self._decision(
                False, "classification_blocked", context, team_id, action, resource_id
            )
        if self.revocation_registry.is_revoked(
            team_id=team_id,
            acl_versions=resource_access.acl_versions(),
        ):
            return self._decision(
                False,
                "source_acl_revoked",
                context,
                team_id,
                action,
                resource_id,
            )

        if context.mode == "public-demo":
            if resource_access.classification != "public_demo":
                return self._decision(
                    False, "non_demo_classification", context, team_id, action, resource_id
                )
            if resource_access.acl_scope != "local_demo":
                return self._decision(
                    False, "non_demo_acl_scope", context, team_id, action, resource_id
                )
            if not self._acl_subject_matches(
                context=context, access=resource_access, allow_empty=True
            ):
                return self._decision(
                    False, "source_acl_denied", context, team_id, action, resource_id
                )
            return self._decision(
                True, "public_demo_allowed", context, team_id, action, resource_id
            )

        if resource_access.acl_scope != "source_acl":
            return self._decision(
                False, "source_acl_unscoped", context, team_id, action, resource_id
            )
        if not resource_access.source_acl_version:
            return self._decision(
                False, "source_acl_version_missing", context, team_id, action, resource_id
            )
        if not self._acl_subject_matches(
            context=context, access=resource_access, allow_empty=False
        ):
            return self._decision(False, "source_acl_denied", context, team_id, action, resource_id)
        return self._decision(True, "source_acl_allowed", context, team_id, action, resource_id)

    def require(
        self,
        *,
        context: AccessContext,
        team_id: str,
        action: AccessAction,
        resource_access: ResourceAccess | None = None,
        resource_id: str | None = None,
    ) -> AccessDecision:
        decision = self.decide(
            context=context,
            team_id=team_id,
            action=action,
            resource_access=resource_access,
            resource_id=resource_id,
        )
        if not decision.allowed:
            raise AccessDeniedError(
                f"Access denied ({decision.reason_code}) for {action} on team {team_id}."
            )
        return decision

    def filter_readable(
        self,
        resources: Iterable[T],
        *,
        context: AccessContext,
        team_id: str,
        access_of: Callable[[T], ResourceAccess | None],
        resource_id_of: Callable[[T], str] | None = None,
    ) -> list[T]:
        readable: list[T] = []
        for resource in resources:
            resource_id = resource_id_of(resource) if resource_id_of else None
            decision = self.decide(
                context=context,
                team_id=team_id,
                action="retrieve",
                resource_access=access_of(resource),
                resource_id=resource_id,
            )
            if decision.allowed:
                readable.append(resource)
        return readable

    def derive_artifact_access(
        self,
        *,
        context: AccessContext,
        team_id: str,
        source_access: Iterable[ResourceAccess],
        requested_access: ResourceAccess,
    ) -> ResourceAccess:
        """Create an artifact ACL that cannot be broader than its inputs."""

        descriptors = [requested_access, *source_access]
        for index, descriptor in enumerate(descriptors):
            self.require(
                context=context,
                team_id=team_id,
                action="retrieve",
                resource_access=descriptor,
                resource_id=f"artifact-source-{index}",
            )
        if context.mode == "public-demo":
            return ResourceAccess()

        classifications = {item.classification for item in descriptors}
        classification = (
            "sensitive"
            if "sensitive" in classifications
            else "internal"
            if "internal" in classifications
            else "public_demo"
        )
        common_groups = set(descriptors[0].allowed_group_ids)
        common_principals = set(descriptors[0].allowed_principal_ids)
        for descriptor in descriptors[1:]:
            common_groups &= descriptor.allowed_group_ids
            common_principals &= descriptor.allowed_principal_ids
        common_principals.add(context.principal.principal_id)

        fingerprint_parts = []
        lineage: set[str] = set()
        for descriptor in descriptors:
            lineage.update(descriptor.acl_versions())
            fingerprint_parts.append(
                "|".join(
                    [
                        descriptor.classification,
                        descriptor.acl_scope,
                        descriptor.source_acl_version or "missing",
                        ",".join(sorted(descriptor.allowed_principal_ids)),
                        ",".join(sorted(descriptor.allowed_group_ids)),
                    ]
                )
            )
        fingerprint = hashlib.sha256(
            "\n".join(sorted(fingerprint_parts)).encode("utf-8")
        ).hexdigest()[:20]
        return ResourceAccess(
            classification=classification,
            acl_scope="source_acl",
            allowed_principal_ids=common_principals,
            allowed_group_ids=common_groups,
            source_acl_version=f"derived:{fingerprint}",
            source_acl_lineage=lineage,
        )

    @staticmethod
    def _team_allowed(*, context: AccessContext, team_id: str) -> bool:
        team_ids = context.principal.team_ids
        if context.mode == "private-extension":
            return team_id in team_ids
        return "*" in team_ids or team_id in team_ids

    @staticmethod
    def _acl_subject_matches(
        *,
        context: AccessContext,
        access: ResourceAccess,
        allow_empty: bool,
    ) -> bool:
        principals = access.allowed_principal_ids
        groups = access.allowed_group_ids
        if not principals and not groups:
            return allow_empty
        return context.principal.principal_id in principals or bool(
            context.principal.group_ids & groups
        )

    @staticmethod
    def _decision(
        allowed: bool,
        reason_code: str,
        context: AccessContext,
        team_id: str,
        action: AccessAction,
        resource_id: str | None,
    ) -> AccessDecision:
        return AccessDecision(
            allowed=allowed,
            reason_code=reason_code,
            action=action,
            team_id=team_id,
            principal_id=context.principal.principal_id,
            resource_id=resource_id,
        )
