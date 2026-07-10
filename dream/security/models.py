# SPDX-License-Identifier: Apache-2.0

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AccessMode = Literal["public-demo", "private-extension"]
AccessAction = Literal[
    "retrieve",
    "source_intake",
    "memory_review",
    "requirement_work",
    "audit_read",
    "security_admin",
]
Classification = Literal["public_demo", "internal", "sensitive", "blocked"]
AclScope = Literal["local_demo", "source_acl", "unscoped"]


class RequestPrincipal(BaseModel):
    """Authenticated caller identity supplied by an approved identity boundary."""

    model_config = ConfigDict(extra="forbid")

    principal_id: str
    authenticated: bool = False
    team_ids: set[str] = Field(default_factory=set)
    group_ids: set[str] = Field(default_factory=set)
    roles: set[str] = Field(default_factory=set)

    @field_validator("principal_id")
    @classmethod
    def _principal_id_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("principal_id must not be blank")
        return normalized


class AccessContext(BaseModel):
    """Security context propagated through retrieval and generation."""

    model_config = ConfigDict(extra="forbid")

    mode: AccessMode
    principal: RequestPrincipal
    request_id: str | None = None

    @classmethod
    def public_demo(cls, *, team_ids: set[str] | None = None) -> "AccessContext":
        return cls(
            mode="public-demo",
            principal=RequestPrincipal(
                principal_id="local-demo-user",
                authenticated=True,
                team_ids=team_ids or {"*"},
                roles={"demo_operator"},
            ),
        )


class ResourceAccess(BaseModel):
    """Source ACL metadata that must travel with every derived resource."""

    model_config = ConfigDict(extra="forbid")

    classification: Classification = "public_demo"
    acl_scope: AclScope = "local_demo"
    allowed_principal_ids: set[str] = Field(default_factory=set)
    allowed_group_ids: set[str] = Field(default_factory=set)
    source_acl_version: str | None = None
    source_acl_lineage: set[str] = Field(default_factory=set)

    @classmethod
    def unscoped_private(cls, *, classification: Classification = "internal") -> "ResourceAccess":
        return cls(classification=classification, acl_scope="unscoped")

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, object]) -> "ResourceAccess":
        """Parse connector/front-matter ACL metadata without silently widening access."""

        classification = str(metadata.get("classification", "public_demo")).strip()
        acl_scope = str(metadata.get("acl_scope", "local_demo")).strip()
        return cls.model_validate(
            {
                "classification": classification,
                "acl_scope": acl_scope,
                "allowed_principal_ids": cls._string_set(metadata.get("allowed_principal_ids")),
                "allowed_group_ids": cls._string_set(metadata.get("allowed_group_ids")),
                "source_acl_version": cls._optional_string(metadata.get("source_acl_version")),
                "source_acl_lineage": cls._string_set(metadata.get("source_acl_lineage")),
            }
        )

    def acl_versions(self) -> set[str]:
        versions = set(self.source_acl_lineage)
        if self.source_acl_version:
            versions.add(self.source_acl_version)
        return versions

    def restrictive_merge(self, other: "ResourceAccess") -> "ResourceAccess":
        """Preserve access only when two derivations carry identical ACLs.

        Aggregates with different source ACLs cannot be represented safely by a
        single descriptor, so private retrieval must deny them until a connector
        supplies a proper multi-source authorization record.
        """

        if self == other:
            return self.model_copy(deep=True)
        if (
            self.classification == "public_demo"
            and other.classification == "public_demo"
            and self.acl_scope == "local_demo"
            and other.acl_scope == "local_demo"
            and not self.allowed_principal_ids
            and not other.allowed_principal_ids
            and not self.allowed_group_ids
            and not other.allowed_group_ids
        ):
            return ResourceAccess()
        classification: Classification = (
            "sensitive"
            if "sensitive" in {self.classification, other.classification}
            else "internal"
        )
        return self.unscoped_private(classification=classification)

    @staticmethod
    def _string_set(value: object) -> set[str]:
        if value is None:
            return set()
        if isinstance(value, str):
            return {item.strip() for item in value.split(",") if item.strip()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return {str(item).strip() for item in value if str(item).strip()}
        raise ValueError("ACL subjects must be a string or list of strings")

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class AccessDecision(BaseModel):
    """Non-sensitive policy result suitable for structured audit records."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason_code: str
    action: AccessAction
    team_id: str
    principal_id: str
    resource_id: str | None = None
