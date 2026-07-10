# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DlpStage = Literal["pre_index", "pre_prompt", "pre_persist", "post_response"]
DlpAction = Literal["redact", "block"]
DlpStatus = Literal["allowed", "blocked"]


class DlpFindingEvidence(BaseModel):
    """Non-sensitive finding metadata; the matched value is never persisted."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    category: str
    severity: Literal["medium", "high", "critical"]
    action: DlpAction
    fingerprint: str
    occurrences: int = 1


class DlpDecisionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    timestamp: str
    policy_version: str
    stage: DlpStage
    status: DlpStatus
    team_id: str
    resource_id_hash: str
    classification: str
    input_hash: str
    output_hash: str
    input_char_count: int
    output_char_count: int
    redaction_count: int
    block_count: int
    findings: list[DlpFindingEvidence] = Field(default_factory=list)


class DlpEventLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "dlp-event-ledger-v1"
    events: list[DlpDecisionEvidence] = Field(default_factory=list)


@dataclass(frozen=True)
class DlpInspection:
    sanitized_text: str
    evidence: DlpDecisionEvidence
