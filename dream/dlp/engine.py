# SPDX-License-Identifier: Apache-2.0

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from dream.core.errors import DlpBlockedError
from dream.dlp.models import (
    DlpAction,
    DlpDecisionEvidence,
    DlpFindingEvidence,
    DlpInspection,
    DlpStage,
)
from dream.dlp.repository import DlpEventRepository

DLP_POLICY_VERSION = "dream-dlp-v1"
DEFAULT_MAX_CHARS = 2_000_000


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    category: str
    severity: str
    action: DlpAction
    pattern: re.Pattern[str]
    replacement: str | Callable[[re.Match[str]], str]
    stages: frozenset[DlpStage]


_ALL_STAGES: frozenset[DlpStage] = frozenset(
    {"pre_index", "pre_prompt", "pre_persist", "post_response"}
)
_INPUT_STAGES: frozenset[DlpStage] = frozenset({"pre_index", "pre_prompt", "pre_persist"})


def _secret_replacement(match: re.Match[str]) -> str:
    return (
        f"{match.group(1)}{match.group(2)}{match.group(3)}"
        f"{match.group(4)}[REDACTED:SECRET]{match.group(4)}"
    )


_RULES = (
    _Rule(
        rule_id="private-key-block-v1",
        category="private_key",
        severity="critical",
        action="block",
        pattern=re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
            r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            re.DOTALL,
        ),
        replacement="[BLOCKED:PRIVATE_KEY]",
        stages=_ALL_STAGES,
    ),
    _Rule(
        rule_id="prompt-injection-block-v1",
        category="prompt_injection",
        severity="critical",
        action="block",
        pattern=re.compile(
            r"(?i)\b(?:ignore|disregard|override)\s+(?:all\s+)?"
            r"(?:previous|prior|system|developer)\s+instructions\b"
        ),
        replacement="[BLOCKED:PROMPT_INJECTION]",
        stages=_INPUT_STAGES,
    ),
    _Rule(
        rule_id="secret-assignment-redact-v1",
        category="secret_assignment",
        severity="high",
        action="redact",
        pattern=re.compile(
            r"(?i)\b(api[_-]?key|client[_-]?secret|secret|password|passwd|token)"
            r"([\"']?)(\s*[:=]\s*)([\"']?)([^\s,;\"']+)(?:\4)"
        ),
        replacement=_secret_replacement,
        stages=_ALL_STAGES,
    ),
    _Rule(
        rule_id="aws-access-key-redact-v1",
        category="aws_access_key",
        severity="high",
        action="redact",
        pattern=re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        replacement="[REDACTED:AWS_ACCESS_KEY]",
        stages=_ALL_STAGES,
    ),
    _Rule(
        rule_id="jwt-redact-v1",
        category="jwt",
        severity="high",
        action="redact",
        pattern=re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."
            r"[A-Za-z0-9_-]{10,}\b"
        ),
        replacement="[REDACTED:JWT]",
        stages=_ALL_STAGES,
    ),
    _Rule(
        rule_id="us-ssn-redact-v1",
        category="us_ssn",
        severity="high",
        action="redact",
        pattern=re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
        replacement="[REDACTED:US_SSN]",
        stages=_ALL_STAGES,
    ),
    _Rule(
        rule_id="email-redact-v1",
        category="email_address",
        severity="medium",
        action="redact",
        pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        replacement="[REDACTED:EMAIL]",
        stages=_ALL_STAGES,
    ),
)


class DefaultDlpEngine:
    policy_version = DLP_POLICY_VERSION

    def __init__(
        self,
        *,
        repository: DlpEventRepository | None = None,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> None:
        if max_chars < 1:
            raise ValueError("DLP max_chars must be positive.")
        self.repository = repository or DlpEventRepository()
        self.max_chars = max_chars

    def inspect(
        self,
        text: str,
        *,
        stage: DlpStage,
        team_id: str,
        resource_id: str,
        classification: str,
    ) -> DlpInspection:
        sanitized = text
        findings: list[DlpFindingEvidence] = []
        if classification == "blocked":
            findings.append(
                self._finding(
                    rule_id="classification-block-v1",
                    category="blocked_classification",
                    severity="critical",
                    action="block",
                    value="classification:blocked",
                )
            )
        if len(text) > self.max_chars:
            findings.append(
                self._finding(
                    rule_id="oversize-content-block-v1",
                    category="oversize_content",
                    severity="critical",
                    action="block",
                    value=_hash(text),
                )
            )
            sanitized = "[BLOCKED:OVERSIZE_CONTENT]"
        else:
            for rule in _RULES:
                if stage not in rule.stages:
                    continue
                matches = list(rule.pattern.finditer(sanitized))
                if not matches:
                    continue
                by_fingerprint: dict[str, int] = {}
                for match in matches:
                    fingerprint = _hash(f"{rule.rule_id}\n{match.group(0)}")
                    by_fingerprint[fingerprint] = by_fingerprint.get(fingerprint, 0) + 1
                findings.extend(
                    DlpFindingEvidence(
                        rule_id=rule.rule_id,
                        category=rule.category,
                        severity=rule.severity,
                        action=rule.action,
                        fingerprint=fingerprint,
                        occurrences=count,
                    )
                    for fingerprint, count in sorted(by_fingerprint.items())
                )
                sanitized = rule.pattern.sub(rule.replacement, sanitized)

        block_count = sum(item.occurrences for item in findings if item.action == "block")
        redaction_count = sum(item.occurrences for item in findings if item.action == "redact")
        evidence = DlpDecisionEvidence(
            event_id=f"dlp-{uuid4().hex[:16]}",
            timestamp=datetime.now(UTC).isoformat(),
            policy_version=self.policy_version,
            stage=stage,
            status="blocked" if block_count else "allowed",
            team_id=team_id or "_unknown",
            resource_id_hash=_hash(resource_id or "_unknown"),
            classification=classification,
            input_hash=_hash(text),
            output_hash=_hash(sanitized),
            input_char_count=len(text),
            output_char_count=len(sanitized),
            redaction_count=redaction_count,
            block_count=block_count,
            findings=findings,
        )
        return DlpInspection(sanitized_text=sanitized, evidence=evidence)

    def enforce(
        self,
        text: str,
        *,
        stage: DlpStage,
        team_id: str,
        resource_id: str,
        classification: str,
    ) -> DlpInspection:
        inspection = self.inspect(
            text,
            stage=stage,
            team_id=team_id,
            resource_id=resource_id,
            classification=classification,
        )
        self.repository.record(inspection.evidence)
        if inspection.evidence.status == "blocked":
            categories = sorted({item.category for item in inspection.evidence.findings})
            raise DlpBlockedError(
                f"DLP blocked {stage} content under {self.policy_version}: " + ", ".join(categories)
            )
        return inspection

    @staticmethod
    def _finding(
        *,
        rule_id: str,
        category: str,
        severity: str,
        action: DlpAction,
        value: str,
    ) -> DlpFindingEvidence:
        return DlpFindingEvidence(
            rule_id=rule_id,
            category=category,
            severity=severity,
            action=action,
            fingerprint=_hash(f"{rule_id}\n{value}"),
        )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
