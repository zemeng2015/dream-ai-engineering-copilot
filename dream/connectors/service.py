# SPDX-License-Identifier: Apache-2.0

from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from dream.connectors.lineage import ArtifactLineageRegistry
from dream.connectors.models import (
    ArtifactLineageRecord,
    ArtifactPurgeReport,
    ConnectorLifecycleEvent,
    ConnectorLifecycleResult,
    ConnectorSourceSnapshot,
    ConnectorSourceState,
)
from dream.connectors.repository import ConnectorLifecycleRepository
from dream.core.errors import AccessDeniedError, NotFoundError
from dream.core.paths import ensure_artifacts_dir, get_audit_db_path
from dream.requirement_cases.repository import RequirementCaseRepository
from dream.security.models import AccessContext, ResourceAccess
from dream.security.policy import DefaultAccessPolicy
from dream.security.revocation import AccessRevocationRegistry

_LIFECYCLE_LOCK = RLock()


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ConnectorLifecycleService:
    """Fail closed first, then physically purge registered derived artifacts."""

    def __init__(
        self,
        *,
        artifacts_dir: Path | None = None,
        lifecycle_repository: ConnectorLifecycleRepository | None = None,
        lineage_registry: ArtifactLineageRegistry | None = None,
        revocation_registry: AccessRevocationRegistry | None = None,
        requirement_repository: RequirementCaseRepository | None = None,
    ) -> None:
        root = (artifacts_dir or ensure_artifacts_dir()).resolve()
        self.lifecycle_repository = lifecycle_repository or ConnectorLifecycleRepository(root)
        self.lineage_registry = lineage_registry or ArtifactLineageRegistry(root)
        self.revocation_registry = revocation_registry or AccessRevocationRegistry(
            root / "pilot-security/access-revocations.json"
        )
        self.requirement_repository = requirement_repository or RequirementCaseRepository(
            get_audit_db_path(),
            lineage_registry=self.lineage_registry,
        )
        self.access_policy = DefaultAccessPolicy(revocation_registry=self.revocation_registry)

    def sync_source(
        self,
        snapshot: ConnectorSourceSnapshot,
        *,
        access_context: AccessContext,
    ) -> ConnectorLifecycleResult:
        self._require_private_source_admin(access_context)
        self._validate_source_access(snapshot)
        self.access_policy.require(
            context=access_context,
            team_id=snapshot.team_id,
            action="source_intake",
            resource_access=snapshot.access,
            resource_id=snapshot.source_key,
        )

        with _LIFECYCLE_LOCK:
            existing = self.lifecycle_repository.try_get(
                team_id=snapshot.team_id,
                connector_id=snapshot.connector_id,
                source_id=snapshot.source_id,
            )
            action = "activated"
            revoked_versions: set[str] = set()
            purge_report = ArtifactPurgeReport(team_id=snapshot.team_id, acl_versions=set())
            first_seen = snapshot.observed_at

            if existing is not None:
                first_seen = existing.first_seen_at
                if existing.status == "deleted":
                    self._validate_replacement(existing, snapshot)
                    action = "reactivated"
                elif self._same_observation(existing, snapshot):
                    action = "unchanged"
                else:
                    self._validate_replacement(existing, snapshot)
                    action = "replaced"

                if action in {"replaced", "reactivated"}:
                    revoked_versions = existing.access.acl_versions()
                    self._revoke_versions(
                        team_id=snapshot.team_id,
                        versions=revoked_versions,
                        actor=access_context.principal.principal_id,
                        reason=f"connector_source_{action}",
                    )
                    purge_report = self._purge(
                        team_id=snapshot.team_id,
                        versions=revoked_versions,
                        reason=f"connector_source_{action}",
                    )
            elif snapshot.previous_source_version is not None:
                raise ValueError("Connector source supplied a previous version but has no state.")

            state = ConnectorSourceState(
                source_key=snapshot.source_key,
                connector_id=snapshot.connector_id,
                source_id=snapshot.source_id,
                team_id=snapshot.team_id,
                source_type=snapshot.source_type,
                source_version=snapshot.source_version,
                content_hash=snapshot.content_hash,
                access=snapshot.access.model_copy(deep=True),
                status="active",
                first_seen_at=first_seen,
                last_seen_at=snapshot.observed_at,
            )
            event = self._event(
                source=state,
                action=action,
                actor=access_context.principal.principal_id,
                previous_source_version=existing.source_version if existing else None,
                revoked_versions=revoked_versions,
                purge_report=purge_report,
            )
            self.lifecycle_repository.record(state=state, event=event)
            return ConnectorLifecycleResult(
                action=action,
                source=state,
                revoked_acl_versions=revoked_versions,
                purge_report=purge_report,
                event=event,
            )

    def delete_source(
        self,
        *,
        team_id: str,
        connector_id: str,
        source_id: str,
        expected_source_version: str,
        reason: str,
        access_context: AccessContext,
    ) -> ConnectorLifecycleResult:
        self._require_private_source_admin(access_context)
        reason_text = reason.strip()
        if not reason_text:
            raise ValueError("Connector source deletion reason is required.")
        with _LIFECYCLE_LOCK:
            existing = self.lifecycle_repository.get(
                team_id=team_id,
                connector_id=connector_id,
                source_id=source_id,
            )
            if existing.status == "deleted":
                raise NotFoundError(f"Connector source is already deleted: {existing.source_key}")
            if existing.source_version != expected_source_version.strip():
                raise ValueError("Connector source version changed before deletion; refresh first.")
            self._require_cleanup_authorized(
                access_context=access_context,
                team_id=team_id,
                access=existing.access,
            )
            revoked_versions = existing.access.acl_versions()
            self._revoke_versions(
                team_id=team_id,
                versions=revoked_versions,
                actor=access_context.principal.principal_id,
                reason=reason_text,
            )
            purge_report = self._purge(
                team_id=team_id,
                versions=revoked_versions,
                reason=reason_text,
            )
            deleted_at = _now()
            state = existing.model_copy(
                update={
                    "status": "deleted",
                    "last_seen_at": deleted_at,
                    "deleted_at": deleted_at,
                    "deleted_by": access_context.principal.principal_id,
                    "deletion_reason": reason_text,
                }
            )
            event = self._event(
                source=state,
                action="deleted",
                actor=access_context.principal.principal_id,
                previous_source_version=existing.source_version,
                revoked_versions=revoked_versions,
                purge_report=purge_report,
            )
            self.lifecycle_repository.record(state=state, event=event)
            return ConnectorLifecycleResult(
                action="deleted",
                source=state,
                revoked_acl_versions=revoked_versions,
                purge_report=purge_report,
                event=event,
            )

    def register_source_copy(
        self,
        *,
        team_id: str,
        connector_id: str,
        source_id: str,
        path: Path,
        access_context: AccessContext,
    ) -> ArtifactLineageRecord:
        """Bind a private local source copy to the connector's current ACL version."""

        self._require_private_source_admin(access_context)
        state = self.lifecycle_repository.get(
            team_id=team_id,
            connector_id=connector_id,
            source_id=source_id,
        )
        if state.status != "active":
            raise NotFoundError(f"Connector source is not active: {state.source_key}")
        self.access_policy.require(
            context=access_context,
            team_id=team_id,
            action="source_intake",
            resource_access=state.access,
            resource_id=state.source_key,
        )
        record = self.lineage_registry.register_path(
            team_id=team_id,
            artifact_kind="connector_source_copy",
            path=path,
            access=state.access,
            must_exist=True,
        )
        if record is None:
            raise ValueError("Connector source copy requires versioned ACL lineage.")
        return record

    def retry_cleanup(
        self,
        *,
        team_id: str,
        connector_id: str,
        source_id: str,
        reason: str,
        access_context: AccessContext,
    ) -> ConnectorLifecycleResult:
        """Retry failed physical cleanup without reactivating a tombstoned source."""

        self._require_private_source_admin(access_context)
        reason_text = reason.strip()
        if not reason_text:
            raise ValueError("Connector cleanup retry reason is required.")
        with _LIFECYCLE_LOCK:
            state = self.lifecycle_repository.get(
                team_id=team_id,
                connector_id=connector_id,
                source_id=source_id,
            )
            if state.status != "deleted":
                raise ValueError("Connector cleanup retry requires a tombstoned source.")
            self._require_cleanup_authorized(
                access_context=access_context,
                team_id=team_id,
                access=state.access,
            )
            versions = state.access.acl_versions()
            purge_report = self._purge(
                team_id=team_id,
                versions=versions,
                reason=f"cleanup_retry: {reason_text}",
            )
            event = self._event(
                source=state,
                action="cleanup_retry",
                actor=access_context.principal.principal_id,
                previous_source_version=state.source_version,
                revoked_versions=versions,
                purge_report=purge_report,
            )
            self.lifecycle_repository.record(state=state, event=event)
            return ConnectorLifecycleResult(
                action="cleanup_retry",
                source=state,
                revoked_acl_versions=versions,
                purge_report=purge_report,
                event=event,
            )

    def _purge(self, *, team_id: str, versions: set[str], reason: str) -> ArtifactPurgeReport:
        return self.lineage_registry.purge(
            team_id=team_id,
            acl_versions=versions,
            reason=reason,
            delete_requirement_case=self.requirement_repository.delete,
        )

    def _revoke_versions(
        self,
        *,
        team_id: str,
        versions: set[str],
        actor: str,
        reason: str,
    ) -> None:
        for version in sorted(versions):
            self.revocation_registry.revoke(
                team_id=team_id,
                source_acl_version=version,
                revoked_by=actor,
                reason=reason,
            )

    @staticmethod
    def _same_observation(
        existing: ConnectorSourceState,
        snapshot: ConnectorSourceSnapshot,
    ) -> bool:
        return (
            existing.source_version == snapshot.source_version
            and existing.content_hash == snapshot.content_hash
            and existing.access == snapshot.access
            and existing.source_type == snapshot.source_type
        )

    @staticmethod
    def _validate_replacement(
        existing: ConnectorSourceState,
        snapshot: ConnectorSourceSnapshot,
    ) -> None:
        if snapshot.previous_source_version != existing.source_version:
            raise ValueError(
                "Connector source observation is stale or missing the expected previous version."
            )
        if existing.content_hash != snapshot.content_hash and (
            existing.source_version == snapshot.source_version
        ):
            raise ValueError("Connector content changed without a new source version.")
        old_acl_version = existing.access.source_acl_version
        new_acl_version = snapshot.access.source_acl_version
        if old_acl_version == new_acl_version:
            raise ValueError("Connector source or ACL changed without a new ACL version.")

    @staticmethod
    def _validate_source_access(snapshot: ConnectorSourceSnapshot) -> None:
        if snapshot.access.acl_scope != "source_acl":
            raise ValueError("Connector sources require source_acl scope.")
        if not snapshot.access.source_acl_version:
            raise ValueError("Connector sources require an immutable source ACL version.")
        if snapshot.access.source_acl_lineage:
            raise ValueError("Primary connector sources cannot declare derived ACL lineage.")

    @staticmethod
    def _require_private_source_admin(access_context: AccessContext) -> None:
        principal = access_context.principal
        if access_context.mode != "private-extension":
            raise AccessDeniedError("Connector lifecycle is available only in private mode.")
        if not principal.authenticated or not (
            {"source_admin", "security_admin"} & principal.roles
        ):
            raise AccessDeniedError("Connector lifecycle requires a verified source administrator.")

    @staticmethod
    def _require_cleanup_authorized(
        *,
        access_context: AccessContext,
        team_id: str,
        access: ResourceAccess,
    ) -> None:
        """Authorize cleanup without letting an existing revocation block deletion."""

        principal = access_context.principal
        if team_id not in principal.team_ids:
            raise AccessDeniedError("Connector cleanup principal is not authorized for this team.")
        if "security_admin" in principal.roles:
            return
        principal_allowed = principal.principal_id in access.allowed_principal_ids
        group_allowed = bool(principal.group_ids & access.allowed_group_ids)
        if not (principal_allowed or group_allowed):
            raise AccessDeniedError("Connector cleanup principal is not allowed by the source ACL.")

    @staticmethod
    def _event(
        *,
        source: ConnectorSourceState,
        action: str,
        actor: str,
        previous_source_version: str | None,
        revoked_versions: set[str],
        purge_report: ArtifactPurgeReport,
    ) -> ConnectorLifecycleEvent:
        return ConnectorLifecycleEvent(
            event_id=f"connector-event-{uuid4().hex[:16]}",
            source_key=source.source_key,
            team_id=source.team_id,
            action=action,
            actor=actor,
            occurred_at=_now(),
            previous_source_version=previous_source_version,
            current_source_version=source.source_version,
            revoked_acl_versions=revoked_versions,
            purged_artifact_ids=[
                item.artifact_id
                for item in purge_report.items
                if item.status in {"purged", "already_absent"}
            ],
            cleanup_complete=purge_report.cleanup_complete,
            warnings=purge_report.warnings,
        )
