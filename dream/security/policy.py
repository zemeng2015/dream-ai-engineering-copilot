# SPDX-License-Identifier: Apache-2.0

import hashlib
from collections.abc import Callable, Iterable
from typing import TypeVar

from dream.core.errors import AccessDeniedError, DreamError
from dream.security.evidence import (
    AccessDecisionReason,
    SecurityDecisionRepository,
    new_access_evidence,
)
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
        decision_repository: SecurityDecisionRepository | None = None,
    ) -> None:
        self.revocation_registry = revocation_registry or AccessRevocationRegistry()
        self.decision_repository = decision_repository
        if self.decision_repository is None and self._private_runtime_configured():
            self.decision_repository = SecurityDecisionRepository()

    @staticmethod
    def _private_runtime_configured() -> bool:
        # Local import avoids a config -> extension -> retriever -> security cycle.
        from dream.config import resolve_config

        return resolve_config().mode == "private-extension"

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

        def finish(allowed: bool, reason_code: AccessDecisionReason) -> AccessDecision:
            return self._decision(
                allowed,
                reason_code,
                context,
                team_id,
                action,
                resource_id,
                resource_access,
            )

        if not principal.authenticated:
            return finish(False, "principal_not_authenticated")
        if not self._team_allowed(context=context, team_id=team_id):
            return finish(False, "team_not_authorized")

        if context.mode == "private-extension" and not (principal.roles & _ACTION_ROLES[action]):
            return finish(False, "role_not_authorized")

        if resource_access is None:
            return finish(False, "resource_acl_missing")
        if resource_access.classification == "blocked":
            return finish(False, "classification_blocked")
        if self.revocation_registry.is_revoked(
            team_id=team_id,
            acl_versions=resource_access.acl_versions(),
        ):
            return finish(False, "source_acl_revoked")

        if context.mode == "public-demo":
            if resource_access.classification != "public_demo":
                return finish(False, "non_demo_classification")
            if resource_access.acl_scope != "local_demo":
                return finish(False, "non_demo_acl_scope")
            if not self._acl_subject_matches(
                context=context, access=resource_access, allow_empty=True
            ):
                return finish(False, "source_acl_denied")
            return finish(True, "public_demo_allowed")

        if resource_access.acl_scope != "source_acl":
            return finish(False, "source_acl_unscoped")
        if not resource_access.source_acl_version:
            return finish(False, "source_acl_version_missing")
        if not self._acl_subject_matches(
            context=context, access=resource_access, allow_empty=False
        ):
            return finish(False, "source_acl_denied")
        return finish(True, "source_acl_allowed")

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

    def _decision(
        self,
        allowed: bool,
        reason_code: AccessDecisionReason,
        context: AccessContext,
        team_id: str,
        action: AccessAction,
        resource_id: str | None,
        resource_access: ResourceAccess | None,
    ) -> AccessDecision:
        decision = AccessDecision(
            allowed=allowed,
            reason_code=reason_code,
            action=action,
            team_id=team_id,
            principal_id=context.principal.principal_id,
            resource_id=resource_id,
        )
        if self.decision_repository is not None:
            try:
                self.decision_repository.record_access(
                    new_access_evidence(
                        allowed=allowed,
                        reason_code=reason_code,
                        mode=context.mode,
                        action=action,
                        team_id=team_id,
                        principal_id=context.principal.principal_id,
                        request_id=context.request_id,
                        resource_id=resource_id,
                        classification=(
                            resource_access.classification if resource_access else None
                        ),
                        acl_scope=(resource_access.acl_scope if resource_access else None),
                        source_acl_versions=(
                            resource_access.acl_versions() if resource_access else set()
                        ),
                    )
                )
            except DreamError as exc:
                raise AccessDeniedError(
                    "Access decision evidence is unavailable."
                ) from exc
        return decision
