# SPDX-License-Identifier: Apache-2.0

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

EVIDENCE_BUNDLE_SCHEMA_VERSION_V1 = "pilot-evidence-bundle-v1"
EVIDENCE_BUNDLE_SCHEMA_VERSION = "pilot-evidence-bundle-v2"
EVIDENCE_SECTION_SCHEMA_VERSION = "pilot-evidence-section-v1"

EvidenceScope = Literal["team", "deployment"]
CoverageStatus = Literal["included", "empty", "missing"]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class EvidenceSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["pilot-evidence-section-v1"] = (
        EVIDENCE_SECTION_SCHEMA_VERSION
    )
    source: str
    scope: EvidenceScope
    records: list[dict[str, object]] = Field(default_factory=list)


class EvidenceCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    scope: EvidenceScope
    status: CoverageStatus
    record_count: int = Field(ge=0)
    source_snapshot_sha256: Sha256 | None = None


class EvidenceFileChecksum(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: Sha256
    size_bytes: int = Field(ge=0)


class PilotEvidenceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[
        "pilot-evidence-bundle-v1",
        "pilot-evidence-bundle-v2",
    ] = EVIDENCE_BUNDLE_SCHEMA_VERSION
    bundle_id: Annotated[
        str,
        StringConstraints(
            pattern=(
                r"^pilot-evidence-[0-9a-f]{12}-"
                r"[0-9]{8}T[0-9]{12}Z-[0-9a-f]{8}$"
            )
        ),
    ]
    generated_at: AwareDatetime
    mode: Literal["public-demo", "private-extension"]
    status: Literal["partial_control_evidence"] = "partial_control_evidence"
    team_id_hash: Sha256
    operator_id_hash: Sha256
    reason_hash: Sha256
    known_coverage_gaps: list[str]
    coverage: list[EvidenceCoverage]
    files: list[EvidenceFileChecksum]
    bundle_root_sha256: Sha256 | None = None


class PilotEvidenceBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    bundle_dir: str
    manifest_path: str
    manifest_sha256: Sha256
    bundle_root_sha256: Sha256
    status: str
    known_coverage_gaps: list[str]


class PilotEvidenceVerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_at: AwareDatetime
    passed: bool
    bundle_id: str | None = None
    bundle_root_sha256: Sha256 | None = None
    expected_root_matched: bool | None = None
    checks: dict[str, bool] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
