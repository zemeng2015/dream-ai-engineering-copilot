# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from dream.core.errors import DreamError, PathTraversalError
from dream.core.paths import PROJECT_ROOT, get_artifacts_dir
from dream.pilot_evidence.exporter import PilotEvidenceVerifier
from dream.pilot_evidence.models import PilotEvidenceManifest

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Ed25519Signature = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9+/]{86}==$"),
]
BundleSchema = Literal["pilot-evidence-bundle-v1", "pilot-evidence-bundle-v2"]
BundleId = Annotated[
    str,
    StringConstraints(
        pattern=(
            r"^pilot-evidence-[0-9a-f]{12}-"
            r"[0-9]{8}T[0-9]{12}Z-[0-9a-f]{8}$"
        )
    ),
]


class EvidenceSignatureClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["pilot-evidence-signature-v1"] = (
        "pilot-evidence-signature-v1"
    )
    algorithm: Literal["Ed25519"] = "Ed25519"
    bundle_schema_version: BundleSchema
    bundle_id: BundleId
    bundle_root_sha256: Sha256
    manifest_sha256: Sha256
    public_key_sha256: Sha256
    key_id_hash: Sha256
    signer_id_hash: Sha256
    reason_hash: Sha256
    signed_at: AwareDatetime


class EvidenceSignatureReceipt(EvidenceSignatureClaims):
    signature: Ed25519Signature


class EvidenceSignatureBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    bundle_root_sha256: Sha256
    receipt_path: str
    receipt_sha256: Sha256
    public_key_sha256: Sha256
    key_id_hash: Sha256
    algorithm: Literal["Ed25519"] = "Ed25519"


class EvidenceSignatureVerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_at: AwareDatetime
    passed: bool
    bundle_id: str | None = None
    bundle_root_sha256: Sha256 | None = None
    public_key_sha256: Sha256 | None = None
    expected_key_id_matched: bool | None = None
    checks: dict[str, bool] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)


class PilotEvidenceSigner:
    """Create a detached Ed25519 receipt for an internally valid bundle."""

    def __init__(
        self,
        *,
        artifacts_dir: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.artifacts_dir = (artifacts_dir or get_artifacts_dir()).resolve()
        self.project_root = (project_root or PROJECT_ROOT).resolve()

    def sign(
        self,
        *,
        bundle_dir: Path,
        expected_root_sha256: str,
        private_key_path: Path,
        key_id: str,
        signer_id: str,
        reason: str,
        private_key_password_env: str | None = None,
        output_path: Path | None = None,
    ) -> EvidenceSignatureBuildResult:
        bundle = self._bundle_path(bundle_dir)
        expected_root = _required_sha256(expected_root_sha256, "expected_root_sha256")
        internal = PilotEvidenceVerifier().verify(
            bundle,
            expected_root_sha256=expected_root,
        )
        if not internal.passed:
            raise DreamError("Evidence bundle failed internal verification and cannot be signed.")
        manifest_path = bundle / "manifest.json"
        try:
            manifest = PilotEvidenceManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            raise DreamError("Evidence bundle manifest is unreadable or invalid.") from exc

        private_key = self._load_private_key(
            private_key_path,
            password_env=private_key_password_env,
        )
        public_key = private_key.public_key()
        public_fingerprint = _public_key_fingerprint(public_key)
        claims = EvidenceSignatureClaims(
            bundle_schema_version=manifest.schema_version,
            bundle_id=manifest.bundle_id,
            bundle_root_sha256=manifest.bundle_root_sha256,
            manifest_sha256=_hash_file(manifest_path),
            public_key_sha256=public_fingerprint,
            key_id_hash=_hash_required(key_id, "key_id"),
            signer_id_hash=_hash_required(signer_id, "signer_id"),
            reason_hash=_hash_required(reason, "reason"),
            signed_at=datetime.now(UTC),
        )
        signature = private_key.sign(_canonical_claims(claims))
        receipt = EvidenceSignatureReceipt(
            **claims.model_dump(),
            signature=base64.b64encode(signature).decode("ascii"),
        )
        post_sign = PilotEvidenceVerifier().verify(
            bundle,
            expected_root_sha256=expected_root,
        )
        if (
            not post_sign.passed
            or _hash_file(manifest_path) != receipt.manifest_sha256
        ):
            raise DreamError("Evidence bundle changed during signing; no receipt was written.")
        destination = self._receipt_path(bundle, output_path)
        try:
            with destination.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    json.dumps(
                        receipt.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                    + "\n"
                )
        except FileExistsError as exc:
            raise DreamError(
                "Evidence signature receipt already exists; overwrite is forbidden."
            ) from exc
        except OSError as exc:
            try:
                if destination.is_file() and not destination.is_symlink():
                    destination.unlink(missing_ok=True)
            except OSError:
                pass
            raise DreamError("Evidence signature receipt could not be written.") from exc
        return EvidenceSignatureBuildResult(
            bundle_id=receipt.bundle_id,
            bundle_root_sha256=receipt.bundle_root_sha256,
            receipt_path=destination.as_posix(),
            receipt_sha256=_hash_file(destination),
            public_key_sha256=receipt.public_key_sha256,
            key_id_hash=receipt.key_id_hash,
        )

    def _bundle_path(self, bundle_dir: Path) -> Path:
        resolved = bundle_dir.resolve()
        if bundle_dir.is_symlink() or not resolved.is_dir():
            raise DreamError("Evidence bundle path is invalid.")
        if not resolved.is_relative_to(self.artifacts_dir):
            raise PathTraversalError("Evidence bundle must stay inside the artifact root.")
        return resolved

    def _receipt_path(self, bundle: Path, output_path: Path | None) -> Path:
        candidate = output_path or bundle.parent / f"{bundle.name}.signature.json"
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.artifacts_dir):
            raise PathTraversalError("Evidence signature receipt must stay inside artifact root.")
        if resolved == bundle or resolved.is_relative_to(bundle):
            raise PathTraversalError(
                "Detached signature receipt cannot enter the bundle directory."
            )
        control = (self.artifacts_dir / "pilot-security").resolve()
        if resolved == control or resolved.is_relative_to(control):
            raise PathTraversalError("Evidence signature receipt cannot enter the control ledger.")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    def _load_private_key(
        self,
        path: Path,
        *,
        password_env: str | None,
    ) -> Ed25519PrivateKey:
        resolved = self._approved_key_path(path, "private")
        password_value = os.getenv(password_env) if password_env else None
        password = password_value.encode("utf-8") if password_value else None
        try:
            key = serialization.load_pem_private_key(
                resolved.read_bytes(),
                password=password,
            )
        except (OSError, TypeError, ValueError, UnsupportedAlgorithm) as exc:
            raise DreamError("Evidence signing private key is unreadable or invalid.") from exc
        if not isinstance(key, Ed25519PrivateKey):
            raise DreamError("Evidence signing requires an Ed25519 private key.")
        return key

    def _approved_key_path(self, path: Path, label: str) -> Path:
        if not path.is_absolute():
            raise PathTraversalError(f"Evidence {label} key path must be absolute.")
        resolved = path.resolve()
        if path.is_symlink() or not resolved.is_file():
            raise DreamError(f"Evidence {label} key path is invalid.")
        if resolved.is_relative_to(self.project_root):
            raise PathTraversalError(
                f"Evidence {label} key must stay outside the public checkout."
            )
        if resolved.is_relative_to(self.artifacts_dir):
            raise PathTraversalError(
                f"Evidence {label} key must stay outside the artifact root."
            )
        return resolved


class PilotEvidenceSignatureVerifier:
    """Verify bundle integrity and its detached Ed25519 custody receipt."""

    def __init__(
        self,
        *,
        artifacts_dir: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.artifacts_dir = (artifacts_dir or get_artifacts_dir()).resolve()
        self.project_root = (project_root or PROJECT_ROOT).resolve()

    def verify(
        self,
        *,
        bundle_dir: Path,
        receipt_path: Path,
        public_key_path: Path,
        expected_key_id: str | None = None,
    ) -> EvidenceSignatureVerificationReport:
        verified_at = datetime.now(UTC)
        checks: dict[str, bool] = {}
        failures: list[str] = []
        bundle = bundle_dir.resolve()
        internal = PilotEvidenceVerifier().verify(bundle_dir)
        checks["bundle_internal"] = not bundle_dir.is_symlink() and internal.passed
        if not checks["bundle_internal"]:
            failures.append("bundle_internal")

        try:
            receipt_resolved = receipt_path.resolve()
            if (
                receipt_path.is_symlink()
                or not receipt_resolved.is_file()
                or receipt_resolved.is_relative_to(bundle)
            ):
                raise ValueError("invalid receipt path")
            receipt = EvidenceSignatureReceipt.model_validate_json(
                receipt_resolved.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return _signature_failure(verified_at, checks, [*failures, "receipt_invalid"])

        try:
            manifest_path = bundle / "manifest.json"
            manifest = PilotEvidenceManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return _signature_failure(
                verified_at,
                checks,
                [*failures, "manifest_invalid"],
                receipt=receipt,
            )

        bundle_match = (
            receipt.bundle_id == manifest.bundle_id
            and receipt.bundle_schema_version == manifest.schema_version
            and receipt.bundle_root_sha256 == manifest.bundle_root_sha256
            and receipt.manifest_sha256 == _hash_file(manifest_path)
        )
        checks["receipt_bundle_binding"] = bundle_match
        if not bundle_match:
            failures.append("receipt_bundle_binding")

        try:
            public_key = self._load_public_key(public_key_path)
        except DreamError:
            return _signature_failure(
                verified_at,
                checks,
                [*failures, "public_key_invalid"],
                receipt=receipt,
            )
        fingerprint = _public_key_fingerprint(public_key)
        checks["public_key_fingerprint"] = fingerprint == receipt.public_key_sha256
        if not checks["public_key_fingerprint"]:
            failures.append("public_key_fingerprint")

        if expected_key_id is not None:
            try:
                expected_key_matched = (
                    _hash_required(expected_key_id, "expected_key_id")
                    == receipt.key_id_hash
                )
            except DreamError:
                expected_key_matched = False
            checks["expected_key_id"] = expected_key_matched
            if not expected_key_matched:
                failures.append("expected_key_id")
        else:
            expected_key_matched = None

        try:
            public_key.verify(
                base64.b64decode(receipt.signature, validate=True),
                _canonical_claims(receipt),
            )
            signature_valid = True
        except (InvalidSignature, ValueError):
            signature_valid = False
        checks["signature"] = signature_valid
        if not signature_valid:
            failures.append("signature")
        return EvidenceSignatureVerificationReport(
            verified_at=verified_at,
            passed=not failures,
            bundle_id=receipt.bundle_id,
            bundle_root_sha256=receipt.bundle_root_sha256,
            public_key_sha256=fingerprint,
            expected_key_id_matched=expected_key_matched,
            checks=checks,
            failures=list(dict.fromkeys(failures)),
        )

    def _load_public_key(self, path: Path) -> Ed25519PublicKey:
        if not path.is_absolute():
            raise PathTraversalError("Evidence public key path must be absolute.")
        resolved = path.resolve()
        if path.is_symlink() or not resolved.is_file():
            raise DreamError("Evidence public key path is invalid.")
        if resolved.is_relative_to(self.project_root):
            raise PathTraversalError(
                "Evidence public key must stay outside the public checkout."
            )
        if resolved.is_relative_to(self.artifacts_dir):
            raise PathTraversalError(
                "Evidence public key must stay outside the artifact root."
            )
        try:
            key = serialization.load_pem_public_key(resolved.read_bytes())
        except (OSError, TypeError, ValueError, UnsupportedAlgorithm) as exc:
            raise DreamError("Evidence public key is unreadable or invalid.") from exc
        if not isinstance(key, Ed25519PublicKey):
            raise DreamError("Evidence verification requires an Ed25519 public key.")
        return key


def _canonical_claims(value: EvidenceSignatureClaims | EvidenceSignatureReceipt) -> bytes:
    payload = value.model_dump(mode="json", exclude={"signature"})
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _public_key_fingerprint(public_key: Ed25519PublicKey) -> str:
    encoded = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(encoded).hexdigest()


def _hash_required(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DreamError(f"Evidence signature {label} is required.")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _required_sha256(value: str, label: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise DreamError(f"Evidence signature {label} must be a SHA-256 digest.")
    return normalized


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _signature_failure(
    verified_at: datetime,
    checks: dict[str, bool],
    failures: list[str],
    *,
    receipt: EvidenceSignatureReceipt | None = None,
) -> EvidenceSignatureVerificationReport:
    return EvidenceSignatureVerificationReport(
        verified_at=verified_at,
        passed=False,
        bundle_id=receipt.bundle_id if receipt else None,
        bundle_root_sha256=receipt.bundle_root_sha256 if receipt else None,
        public_key_sha256=receipt.public_key_sha256 if receipt else None,
        checks=checks,
        failures=list(dict.fromkeys(failures)),
    )
