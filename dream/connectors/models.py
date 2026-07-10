# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dream.security.models import ResourceAccess

ConnectorSourceStatus = Literal["active", "deleted"]
ConnectorLifecycleAction = Literal[
    "activated",
    "unchanged",
    "replaced",
    "reactivated",
    "deleted",
    "cleanup_retry",
]
ArtifactLocatorKind = Literal["file", "directory", "requirement_case"]
ArtifactCleanupStatus = Literal["active", "purged", "cleanup_failed"]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def connector_source_key(*, team_id: str, connector_id: str, source_id: str) -> str:
    payload = json.dumps(
        [team_id, connector_id, source_id],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"connector-source:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


class ConnectorSourceSnapshot(BaseModel):
    """Metadata-only connector observation; source bodies never enter this ledger."""

    model_config = ConfigDict(extra="forbid")

    connector_id: str
    source_id: str
    team_id: str
    source_type: str
    source_version: str
    previous_source_version: str | None = None
    content_hash: str
    access: ResourceAccess
    observed_at: str = Field(default_factory=_now)

    @field_validator(
        "connector_id",
        "source_id",
        "team_id",
        "source_type",
        "source_version",
        "content_hash",
    )
    @classmethod
    def _non_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Connector source identifiers and versions must not be blank.")
        return normalized

    @field_validator("previous_source_version")
    @classmethod
    def _optional_version_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Previous source version must be omitted or non-blank.")
        return normalized

    @property
    def source_key(self) -> str:
        return connector_source_key(
            team_id=self.team_id,
            connector_id=self.connector_id,
            source_id=self.source_id,
        )


class ConnectorSourceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    connector_id: str
    source_id: str
    team_id: str
    source_type: str
    source_version: str
    content_hash: str
    access: ResourceAccess
    status: ConnectorSourceStatus = "active"
    first_seen_at: str
    last_seen_at: str
    deleted_at: str | None = None
    deleted_by: str | None = None
    deletion_reason: str | None = None


class ConnectorLifecycleEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    source_key: str
    team_id: str
    action: ConnectorLifecycleAction
    actor: str
    occurred_at: str
    previous_source_version: str | None = None
    current_source_version: str | None = None
    revoked_acl_versions: set[str] = Field(default_factory=set)
    purged_artifact_ids: list[str] = Field(default_factory=list)
    cleanup_complete: bool = True
    warnings: list[str] = Field(default_factory=list)


class ConnectorLifecycleLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "connector-source-lifecycle-v1"
    states: list[ConnectorSourceState] = Field(default_factory=list)
    events: list[ConnectorLifecycleEvent] = Field(default_factory=list)


class ArtifactLineageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    team_id: str
    artifact_kind: str
    locator_kind: ArtifactLocatorKind
    locator: str
    acl_versions: set[str]
    status: ArtifactCleanupStatus = "active"
    registered_at: str
    purged_at: str | None = None
    purge_reason: str | None = None
    cleanup_error: str | None = None


class ArtifactLineageLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "artifact-lineage-v1"
    records: list[ArtifactLineageRecord] = Field(default_factory=list)


class ArtifactPurgeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    status: Literal["purged", "already_absent", "cleanup_failed"]
    error: str | None = None


class ArtifactPurgeReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    acl_versions: set[str]
    items: list[ArtifactPurgeItem] = Field(default_factory=list)
    cleanup_complete: bool = True
    warnings: list[str] = Field(default_factory=list)


class ConnectorLifecycleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ConnectorLifecycleAction
    source: ConnectorSourceState
    revoked_acl_versions: set[str] = Field(default_factory=set)
    purge_report: ArtifactPurgeReport
    event: ConnectorLifecycleEvent
