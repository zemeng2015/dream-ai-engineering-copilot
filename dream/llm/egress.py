# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from dream.core.errors import ProviderConfigurationError
from dream.core.paths import PROJECT_ROOT
from dream.llm.base import BaseLLMProvider, LLMRequest, LLMResponse

if TYPE_CHECKING:
    from dream.config.models import ResolvedDreamConfig

APPROVAL_FILE_ENV = "DREAM_LLM_APPROVAL_FILE"
APPROVAL_SCHEMA_VERSION = "provider-approval-v1"
_EGRESS_LEDGER_LOCK = Lock()


class ProviderApprovalManifest(BaseModel):
    """Deployment-owned exact provider approval; credentials are never part of it."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["provider-approval-v1"] = APPROVAL_SCHEMA_VERSION
    approval_id: str = Field(min_length=1)
    provider: Literal["openai-compatible", "qwen-cloud"]
    base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)
    approved_by: str = Field(min_length=1)
    approved_at: datetime
    expires_at: datetime

    @field_validator("approval_id", "model", "approved_by")
    @classmethod
    def _strip_nonempty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("approval fields must not be blank")
        return normalized

    @field_validator("approved_at", "expires_at")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("approval timestamps must include a timezone")
        return value


class ProviderEgressEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    status: Literal["allowed", "blocked"]
    reason_code: str
    provider: str
    model: str | None = None
    base_url_hash: str | None = None
    approval_id: str | None = None
    manifest_hash: str | None = None


class ProviderEgressRepository:
    """Append-only metadata evidence for local provider-boundary decisions."""

    def __init__(self, artifacts_dir: Path) -> None:
        self.path = artifacts_dir.resolve() / "pilot-security/provider-egress-events.jsonl"

    def record(self, evidence: ProviderEgressEvidence) -> None:
        with _EGRESS_LEDGER_LOCK:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(evidence.model_dump_json() + "\n")

    def load(self) -> list[ProviderEgressEvidence]:
        if not self.path.exists():
            return []
        try:
            return [
                ProviderEgressEvidence.model_validate_json(line)
                for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, ValueError) as exc:
            raise ProviderConfigurationError(
                "Provider egress evidence ledger is unreadable or invalid."
            ) from exc


class ProviderEgressPolicy:
    """Fail closed when a private deployment lacks an exact endpoint/model approval."""

    def __init__(self, repository: ProviderEgressRepository | None = None) -> None:
        self.repository = repository

    def require_approved(
        self,
        config: ResolvedDreamConfig,
    ) -> ProviderApprovalManifest | None:
        if config.mode != "private-extension":
            return None
        provider = config.llm.provider
        model = config.llm.model
        base_url = config.llm.base_url
        if provider == "mock":
            self._record(
                status="allowed",
                reason_code="local_provider_no_egress",
                provider=provider,
                model=model,
                base_url=base_url,
            )
            return None
        if provider == "plugin":
            self._deny(
                reason_code="private_plugin_provider_not_attested",
                provider=provider,
                model=model,
                base_url=base_url,
            )
        if provider not in {"openai-compatible", "qwen-cloud"}:
            self._deny(
                reason_code="unsupported_private_provider",
                provider=provider,
                model=model,
                base_url=base_url,
            )
        if not model or not base_url:
            self._deny(
                reason_code="provider_identity_incomplete",
                provider=provider,
                model=model,
                base_url=base_url,
            )
        try:
            normalized_base_url = normalize_provider_base_url(base_url, require_https=True)
        except ProviderConfigurationError:
            self._deny(
                reason_code="provider_endpoint_invalid",
                provider=provider,
                model=model,
                base_url=base_url,
            )
        manifest, manifest_hash = self._load_manifest(
            provider=provider,
            model=model,
            base_url=normalized_base_url,
        )
        try:
            approved_base_url = normalize_provider_base_url(
                manifest.base_url,
                require_https=True,
            )
        except ProviderConfigurationError:
            self._deny(
                reason_code="approval_endpoint_invalid",
                provider=provider,
                model=model,
                base_url=normalized_base_url,
                approval=manifest,
                manifest_hash=manifest_hash,
            )
        now = datetime.now(UTC)
        if manifest.approved_at.astimezone(UTC) > now:
            self._deny(
                reason_code="approval_not_yet_valid",
                provider=provider,
                model=model,
                base_url=normalized_base_url,
                approval=manifest,
                manifest_hash=manifest_hash,
            )
        if manifest.expires_at.astimezone(UTC) <= now:
            self._deny(
                reason_code="approval_expired",
                provider=provider,
                model=model,
                base_url=normalized_base_url,
                approval=manifest,
                manifest_hash=manifest_hash,
            )
        if (
            manifest.provider != provider
            or manifest.model != model
            or approved_base_url != normalized_base_url
        ):
            self._deny(
                reason_code="approval_identity_mismatch",
                provider=provider,
                model=model,
                base_url=normalized_base_url,
                approval=manifest,
                manifest_hash=manifest_hash,
            )
        self._record(
            status="allowed",
            reason_code="exact_approval_match",
            provider=provider,
            model=model,
            base_url=normalized_base_url,
            approval=manifest,
            manifest_hash=manifest_hash,
        )
        return manifest

    def require_response_identity(
        self,
        config: ResolvedDreamConfig,
        response: LLMResponse,
    ) -> None:
        if config.mode != "private-extension" or config.llm.provider == "mock":
            return
        if (
            response.provider_name != config.llm.provider
            or response.model_name != config.llm.model
        ):
            self._deny(
                reason_code="response_identity_mismatch",
                provider=config.llm.provider,
                model=config.llm.model,
                base_url=config.llm.base_url,
            )

    def require_runtime_identity(
        self,
        config: ResolvedDreamConfig,
        provider: BaseLLMProvider,
    ) -> None:
        if config.mode != "private-extension" or config.llm.provider == "mock":
            return
        observed_base_url = getattr(provider, "base_url", None)
        try:
            normalized_observed_url = normalize_provider_base_url(
                str(observed_base_url or ""),
                require_https=True,
            )
            normalized_config_url = normalize_provider_base_url(
                str(config.llm.base_url or ""),
                require_https=True,
            )
        except ProviderConfigurationError:
            normalized_observed_url = "_invalid"
            normalized_config_url = "_configured"
        if (
            provider.provider_name != config.llm.provider
            or provider.model_name != config.llm.model
            or normalized_observed_url != normalized_config_url
        ):
            self._deny(
                reason_code="runtime_provider_identity_mismatch",
                provider=config.llm.provider,
                model=config.llm.model,
                base_url=config.llm.base_url,
            )

    def _load_manifest(
        self,
        *,
        provider: str,
        model: str,
        base_url: str,
    ) -> tuple[ProviderApprovalManifest, str]:
        raw_path = os.getenv(APPROVAL_FILE_ENV, "").strip()
        if not raw_path:
            self._deny(
                reason_code="approval_file_not_configured",
                provider=provider,
                model=model,
                base_url=base_url,
            )
        path = Path(os.path.expandvars(os.path.expanduser(raw_path)))
        if not path.is_absolute():
            self._deny(
                reason_code="approval_file_path_not_absolute",
                provider=provider,
                model=model,
                base_url=base_url,
            )
        resolved = path.resolve()
        if resolved.is_relative_to(PROJECT_ROOT.resolve()):
            self._deny(
                reason_code="approval_file_inside_public_checkout",
                provider=provider,
                model=model,
                base_url=base_url,
            )
        try:
            raw = resolved.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            manifest = ProviderApprovalManifest.model_validate(payload)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            self._deny(
                reason_code="approval_file_invalid",
                provider=provider,
                model=model,
                base_url=base_url,
            )
        return manifest, _hash_bytes(raw)

    def _deny(
        self,
        *,
        reason_code: str,
        provider: str,
        model: str | None,
        base_url: str | None,
        approval: ProviderApprovalManifest | None = None,
        manifest_hash: str | None = None,
    ) -> None:
        self._record(
            status="blocked",
            reason_code=reason_code,
            provider=provider,
            model=model,
            base_url=base_url,
            approval=approval,
            manifest_hash=manifest_hash,
        )
        raise ProviderConfigurationError(
            f"Private provider egress denied ({reason_code})."
        )

    def _record(
        self,
        *,
        status: Literal["allowed", "blocked"],
        reason_code: str,
        provider: str,
        model: str | None,
        base_url: str | None,
        approval: ProviderApprovalManifest | None = None,
        manifest_hash: str | None = None,
    ) -> None:
        if self.repository is None:
            return
        self.repository.record(
            ProviderEgressEvidence(
                timestamp=datetime.now(UTC).isoformat(),
                status=status,
                reason_code=reason_code,
                provider=provider,
                model=model,
                base_url_hash=_hash_text(base_url) if base_url else None,
                approval_id=approval.approval_id if approval else None,
                manifest_hash=manifest_hash,
            )
        )


class EgressGuardedLLMProvider:
    """Revalidate private provider approval immediately before every invocation."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        *,
        config: ResolvedDreamConfig,
        policy: ProviderEgressPolicy,
    ) -> None:
        self.provider = provider
        self.config = config
        self.policy = policy
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name

    def complete(self, prompt: str | LLMRequest) -> LLMResponse:
        self.policy.require_approved(self.config)
        self.policy.require_runtime_identity(self.config, self.provider)
        response = self.provider.complete(prompt)
        self.policy.require_response_identity(self.config, response)
        return response


def require_private_provider_selector(
    requested: str,
    *,
    config: ResolvedDreamConfig,
) -> None:
    """Prevent request/CLI parameters from selecting a live provider in private mode."""

    if config.mode != "private-extension":
        return
    if requested in {"mock", "deterministic", "none", "config"}:
        return
    raise ProviderConfigurationError(
        "Private mode forbids request-level live provider overrides; use 'config'."
    )


def normalize_provider_base_url(value: str, *, require_https: bool = False) -> str:
    raw = value.strip()
    if not raw or any(char.isspace() for char in raw) or "\\" in raw:
        raise ProviderConfigurationError("Provider base URL is invalid.")
    try:
        parsed = urlparse(raw)
        port = parsed.port
    except ValueError as exc:
        raise ProviderConfigurationError("Provider base URL is invalid.") from exc
    host = parsed.hostname
    if not host or host.endswith(".") or parsed.username is not None or parsed.password is not None:
        raise ProviderConfigurationError("Provider base URL is invalid.")
    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ProviderConfigurationError("Provider base URL is invalid.") from exc
    loopback = ascii_host == "localhost"
    try:
        loopback = loopback or ipaddress.ip_address(ascii_host).is_loopback
    except ValueError:
        pass
    valid_scheme = parsed.scheme == "https" or (
        not require_https and parsed.scheme == "http" and loopback
    )
    path_parts = [part for part in parsed.path.split("/") if part]
    if (
        not valid_scheme
        or parsed.params
        or parsed.query
        or parsed.fragment
        or "%" in parsed.path
        or "//" in parsed.path
        or any(part in {".", ".."} for part in path_parts)
    ):
        raise ProviderConfigurationError("Provider base URL is invalid.")
    if require_https:
        try:
            if ipaddress.ip_address(ascii_host):
                raise ProviderConfigurationError(
                    "Private provider base URL must use an approved DNS hostname."
                )
        except ValueError:
            pass
    host_for_url = f"[{ascii_host}]" if ":" in ascii_host else ascii_host
    netloc = (
        f"{host_for_url}:{port}"
        if port is not None and not (parsed.scheme == "https" and port == 443)
        else host_for_url
    )
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, netloc, path, "", "", ""))


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
