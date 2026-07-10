# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from dream.core.errors import DreamError
from dream.core.paths import ensure_artifacts_dir
from dream.security.models import AccessAction, AccessMode, AclScope, Classification

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
IdentityDecisionStatus = Literal["allowed", "blocked", "error"]
IdentityDecisionReason = Literal[
    "signature_valid",
    "identity_header_missing",
    "team_membership_missing",
    "roles_missing",
    "wildcard_team_forbidden",
    "timestamp_invalid",
    "replay_window_exceeded",
    "key_id_invalid",
    "signature_invalid",
    "identity_boundary_not_configured",
    "identity_evidence_unavailable",
]
AccessDecisionReason = Literal[
    "principal_not_authenticated",
    "team_not_authorized",
    "role_not_authorized",
    "resource_acl_missing",
    "classification_blocked",
    "source_acl_revoked",
    "non_demo_classification",
    "non_demo_acl_scope",
    "source_acl_denied",
    "public_demo_allowed",
    "source_acl_unscoped",
    "source_acl_version_missing",
    "source_acl_allowed",
]

_IDENTITY_LOCK = Lock()
_ACCESS_LOCK = Lock()


class IdentityDecisionEvidence(BaseModel):
    """Metadata-only result from the signed proxy identity boundary."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["identity-decision-v1"] = "identity-decision-v1"
    event_id: str = Field(min_length=1)
    timestamp: AwareDatetime
    status: IdentityDecisionStatus
    reason_code: IdentityDecisionReason
    team_id_hashes: list[Sha256] = Field(default_factory=list)
    principal_id_hash: Sha256 | None = None
    request_id_hash: Sha256 | None = None
    request_target_hash: Sha256
    method_hash: Sha256
    team_count: int = Field(ge=0)
    group_count: int = Field(ge=0)
    role_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _trusted_subjects_only_on_success(self) -> IdentityDecisionEvidence:
        if self.status == "allowed":
            if self.reason_code != "signature_valid":
                raise ValueError("Allowed identity evidence must be signature_valid.")
            if not self.team_id_hashes or self.principal_id_hash is None:
                raise ValueError("Allowed identity evidence requires trusted subjects.")
        elif self.team_id_hashes or self.principal_id_hash is not None:
            raise ValueError("Rejected identity evidence cannot trust asserted subjects.")
        return self


class AccessPolicyDecisionEvidence(BaseModel):
    """Metadata-only result from the default source access policy."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["access-policy-decision-v1"] = (
        "access-policy-decision-v1"
    )
    event_id: str = Field(min_length=1)
    timestamp: AwareDatetime
    allowed: bool
    reason_code: AccessDecisionReason
    mode: AccessMode
    action: AccessAction
    team_id_hash: Sha256
    principal_id_hash: Sha256
    request_id_hash: Sha256 | None = None
    resource_id_hash: Sha256 | None = None
    classification: Classification | None = None
    acl_scope: AclScope | None = None
    source_acl_version_hashes: list[Sha256] = Field(default_factory=list)


class SecurityDecisionRepository:
    """Append-only local evidence for identity and source-policy decisions."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        root = (artifacts_dir or ensure_artifacts_dir()).resolve()
        control = root / "pilot-security"
        self.identity_path = control / "identity-decisions.jsonl"
        self.access_path = control / "access-policy-decisions.jsonl"

    def record_identity(self, evidence: IdentityDecisionEvidence) -> None:
        self._append(self.identity_path, evidence.model_dump_json(), _IDENTITY_LOCK)

    def record_access(self, evidence: AccessPolicyDecisionEvidence) -> None:
        self._append(self.access_path, evidence.model_dump_json(), _ACCESS_LOCK)

    def load_identity(self) -> list[IdentityDecisionEvidence]:
        return self._load(self.identity_path, IdentityDecisionEvidence)

    def load_access(self) -> list[AccessPolicyDecisionEvidence]:
        return self._load(self.access_path, AccessPolicyDecisionEvidence)

    @staticmethod
    def _append(path: Path, payload: str, lock: Lock) -> None:
        try:
            with lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(payload + "\n")
        except OSError as exc:
            raise DreamError("Security decision evidence could not be persisted.") from exc

    @staticmethod
    def _load(path: Path, model_type):
        if not path.exists():
            return []
        try:
            return [
                model_type.model_validate_json(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, ValueError) as exc:
            raise DreamError("Security decision evidence is unreadable or invalid.") from exc


def hash_evidence_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_identity_evidence(
    *,
    status: IdentityDecisionStatus,
    reason_code: IdentityDecisionReason,
    method: str,
    request_target: str,
    team_ids: set[str] | None = None,
    principal_id: str | None = None,
    request_id: str | None = None,
    group_count: int = 0,
    role_count: int = 0,
) -> IdentityDecisionEvidence:
    trusted_teams = sorted(team_ids or set()) if status == "allowed" else []
    return IdentityDecisionEvidence(
        event_id=f"identity-{uuid4().hex}",
        timestamp=datetime.now(UTC),
        status=status,
        reason_code=reason_code,
        team_id_hashes=[hash_evidence_value(item) for item in trusted_teams],
        principal_id_hash=(
            hash_evidence_value(principal_id)
            if status == "allowed" and principal_id is not None
            else None
        ),
        request_id_hash=(hash_evidence_value(request_id) if request_id else None),
        request_target_hash=hash_evidence_value(request_target),
        method_hash=hash_evidence_value(method.upper()),
        team_count=len(trusted_teams),
        group_count=group_count if status == "allowed" else 0,
        role_count=role_count if status == "allowed" else 0,
    )


def new_access_evidence(
    *,
    allowed: bool,
    reason_code: AccessDecisionReason,
    mode: AccessMode,
    action: AccessAction,
    team_id: str,
    principal_id: str,
    request_id: str | None,
    resource_id: str | None,
    classification: Classification | None,
    acl_scope: AclScope | None,
    source_acl_versions: set[str],
) -> AccessPolicyDecisionEvidence:
    return AccessPolicyDecisionEvidence(
        event_id=f"access-{uuid4().hex}",
        timestamp=datetime.now(UTC),
        allowed=allowed,
        reason_code=reason_code,
        mode=mode,
        action=action,
        team_id_hash=hash_evidence_value(team_id),
        principal_id_hash=hash_evidence_value(principal_id),
        request_id_hash=(hash_evidence_value(request_id) if request_id else None),
        resource_id_hash=(hash_evidence_value(resource_id) if resource_id else None),
        classification=classification,
        acl_scope=acl_scope,
        source_acl_version_hashes=sorted(
            hash_evidence_value(item) for item in source_acl_versions
        ),
    )
