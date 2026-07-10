# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from dream.core.errors import DreamError
from dream.core.paths import PROJECT_ROOT

RELEASE_SCHEMA_VERSION = "leadership-release-v1"

CRITICAL_SOURCE_PATHS = [
    "README.md",
    "docs/product-current-state.md",
    "docs/enterprise-pilot-boundary.md",
    "docs/controlled-enterprise-pilot-proposal.md",
    "docs/leadership-demo-runbook.md",
    "docs/leadership-ab-benchmark.md",
    "docs/leadership-product-readiness-audit.md",
    "docs/leadership-release-process.md",
    "docs/pilot-security-foundation.md",
    "docs/frontend-dependency-security.md",
    "docs/connector-lifecycle-foundation.md",
    "docs/dlp-enforcement-foundation.md",
    "docs/provider-egress-foundation.md",
    "docs/security-decision-evidence-foundation.md",
    "docs/pilot-evidence-export-foundation.md",
    "docs/pilot-evidence-custody-foundation.md",
    "docs/private-extension-guide.md",
    "docs/current-development-handoff.md",
    "pyproject.toml",
    "frontend/package.json",
    "frontend/package-lock.json",
    "dream/api/security.py",
    "dream/config/loader.py",
    "dream/config/models.py",
    "dream/config/validator.py",
    "dream/extensions/loader.py",
    "dream/security/identity.py",
    "dream/security/policy.py",
    "dream/security/evidence.py",
    "dream/security/revocation.py",
    "dream/connectors/service.py",
    "dream/connectors/repository.py",
    "dream/connectors/lineage.py",
    "dream/dlp/engine.py",
    "dream/dlp/repository.py",
    "dream/llm/egress.py",
    "dream/llm/openai_compatible.py",
    "dream/pilot_evidence/models.py",
    "dream/pilot_evidence/exporter.py",
    "dream/pilot_evidence/custody.py",
    "dream/leadership_demo/benchmark.py",
    "dream/leadership_demo/preflight.py",
    "dream/leadership_demo/rehearsal.py",
    "dream/leadership_demo/release.py",
    "dream/leadership_demo/service.py",
    "scripts/run_leadership_ab_benchmark.py",
    "scripts/run_leadership_preflight.py",
    "scripts/run_leadership_rehearsal.py",
    "scripts/seed_leadership_demo.py",
    "scripts/build_leadership_release.py",
    "scripts/verify_leadership_release.py",
    "frontend/src/app/core/product-profile.ts",
    "frontend/src/app/features/leadership-demo/leadership-demo.component.ts",
    "knowledge_packs/demo_team/eval_profiles/async-status-tracking.yaml",
    "knowledge_packs/demo_team/team.yaml",
]


class GitReleaseState(BaseModel):
    branch: str
    commit_sha: str
    status_lines: list[str] = Field(default_factory=list)

    @property
    def dirty(self) -> bool:
        return bool(self.status_lines)


class FileChecksum(BaseModel):
    path: str
    sha256: str
    size_bytes: int


class LeadershipReleaseManifest(BaseModel):
    schema_version: Literal["leadership-release-v1"] = RELEASE_SCHEMA_VERSION
    release_id: str
    created_at: str
    status: Literal["candidate_uncommitted", "frozen"]
    branch: str
    commit_sha: str
    dirty: bool
    git_status_lines: list[str] = Field(default_factory=list)
    source_file_count: int
    source_snapshot_sha256: str
    critical_source_checksums: list[FileChecksum]
    evidence_artifact_checksums: list[FileChecksum]
    frontend_bundle_file_count: int
    frontend_bundle_sha256: str
    preflight_ready: bool
    preflight_warnings: list[str] = Field(default_factory=list)
    rehearsal_passed: bool
    rehearsal_baseline_restored: bool
    rehearsal_external_writes_performed: bool
    benchmark_evidence_tier: str
    benchmark_repetitions: int
    benchmark_same_provider_verified: bool
    benchmark_same_model_verified: bool
    benchmark_same_request_verified: bool
    benchmark_same_contract_verified: bool
    warnings: list[str] = Field(default_factory=list)


class ReleaseVerificationReport(BaseModel):
    verified_at: str
    passed: bool
    release_id: str
    status: str
    checks: dict[str, bool]
    failures: list[str] = Field(default_factory=list)


class LeadershipReleaseBuilder:
    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        git_state: GitReleaseState | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.git_state = git_state

    def build(
        self,
        *,
        output_dir: Path,
        strict: bool = False,
    ) -> LeadershipReleaseManifest:
        git_state = self.git_state or self._read_git_state()
        self._validate_product_branch(git_state.branch)
        if strict and git_state.dirty:
            raise DreamError("Strict leadership release requires a clean working tree.")

        preflight_path = (
            self.project_root / "artifacts/leadership-preflight/leadership-preflight.json"
        )
        rehearsal_path = (
            self.project_root / "artifacts/leadership-rehearsal/leadership-rehearsal.json"
        )
        benchmark_path = self.project_root / (
            "artifacts/leadership-preflight/benchmark/"
            "leadership-ab-benchmark-suite.json"
        )
        preflight = self._load_json(preflight_path, "leadership preflight")
        rehearsal = self._load_json(rehearsal_path, "leadership rehearsal")
        benchmark = self._load_json(benchmark_path, "leadership benchmark suite")
        self._validate_evidence(preflight, rehearsal, benchmark, strict=strict)

        source_paths = self._git_visible_paths()
        source_snapshot_hash = _hash_path_set(self.project_root, source_paths)
        critical_checksums = [
            _checksum(self.project_root, self.project_root / relative_path)
            for relative_path in CRITICAL_SOURCE_PATHS
        ]
        evidence_paths = [
            preflight_path,
            preflight_path.with_suffix(".md"),
            rehearsal_path,
            rehearsal_path.with_suffix(".md"),
            benchmark_path,
            benchmark_path.with_suffix(".md"),
        ]
        evidence_checksums = [
            _checksum(self.project_root, path) for path in evidence_paths
        ]
        frontend_dir = self.project_root / "frontend/dist/frontend/browser"
        frontend_paths = sorted(path for path in frontend_dir.rglob("*") if path.is_file())
        if not frontend_paths:
            raise DreamError("Angular production bundle is missing.")
        frontend_hash = _hash_path_set(self.project_root, frontend_paths)

        status = "frozen" if strict and not git_state.dirty else "candidate_uncommitted"
        warnings = []
        if git_state.dirty:
            warnings.append(
                "Source snapshot contains uncommitted changes; rerun after review/commit "
                "with --strict."
            )
        if benchmark.get("evidence_tier") != "live_model_evidence":
            warnings.append(
                "Benchmark is harness validation, not approved live-model evidence."
            )
        if not benchmark.get("sme_reference_proof"):
            warnings.append("No approved SME reference is attached.")
        if not benchmark.get("pricing_proof"):
            warnings.append("No approved provider pricing evidence is attached.")

        release_id = (
            f"leadership-{git_state.commit_sha[:12]}-{source_snapshot_hash[:12]}"
        )
        manifest = LeadershipReleaseManifest(
            release_id=release_id,
            created_at=datetime.now(UTC).isoformat(),
            status=status,
            branch=git_state.branch,
            commit_sha=git_state.commit_sha,
            dirty=git_state.dirty,
            git_status_lines=git_state.status_lines,
            source_file_count=len(source_paths),
            source_snapshot_sha256=source_snapshot_hash,
            critical_source_checksums=critical_checksums,
            evidence_artifact_checksums=evidence_checksums,
            frontend_bundle_file_count=len(frontend_paths),
            frontend_bundle_sha256=frontend_hash,
            preflight_ready=bool(preflight.get("ready_for_demo")),
            preflight_warnings=list(preflight.get("warnings") or []),
            rehearsal_passed=bool(rehearsal.get("passed")),
            rehearsal_baseline_restored=bool(rehearsal.get("baseline_restored")),
            rehearsal_external_writes_performed=bool(
                rehearsal.get("external_writes_performed")
            ),
            benchmark_evidence_tier=str(benchmark.get("evidence_tier") or "missing"),
            benchmark_repetitions=int(benchmark.get("repetitions") or 0),
            benchmark_same_provider_verified=bool(
                benchmark.get("same_provider_verified")
            ),
            benchmark_same_model_verified=bool(benchmark.get("same_model_verified")),
            benchmark_same_request_verified=bool(
                benchmark.get("same_request_verified")
            ),
            benchmark_same_contract_verified=bool(
                benchmark.get("same_contract_verified")
            ),
            warnings=warnings,
        )
        self._write_manifest(manifest, output_dir)
        return manifest

    def _validate_evidence(
        self,
        preflight: dict,
        rehearsal: dict,
        benchmark: dict,
        *,
        strict: bool,
    ) -> None:
        if not preflight.get("ready_for_demo"):
            raise DreamError("Leadership preflight is not ready for demo.")
        if not rehearsal.get("passed") or not rehearsal.get("baseline_restored"):
            raise DreamError("Leadership rehearsal did not pass and restore baseline.")
        if rehearsal.get("external_writes_performed"):
            raise DreamError("Leadership rehearsal reports an external write.")
        integrity = [
            benchmark.get("same_provider_verified"),
            benchmark.get("same_model_verified"),
            benchmark.get("same_request_verified"),
            benchmark.get("same_contract_verified"),
        ]
        if int(benchmark.get("repetitions") or 0) < 3 or not all(integrity):
            raise DreamError("Leadership benchmark suite integrity is incomplete.")
        if strict:
            git_check = next(
                (
                    item
                    for item in preflight.get("checks") or []
                    if item.get("check_id") == "git_hygiene"
                ),
                None,
            )
            if not git_check or git_check.get("status") != "pass":
                raise DreamError(
                    "Strict release requires a preflight report with clean git hygiene."
                )

    @staticmethod
    def _validate_product_branch(branch: str) -> None:
        normalized = branch.lower()
        if any(value in normalized for value in ["qwen", "champion", "hackathon"]):
            raise DreamError("Leadership release cannot be built from a competition branch.")

    @staticmethod
    def _load_json(path: Path, label: str) -> dict:
        if not path.exists():
            raise DreamError(f"Missing {label} artifact: {path}")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise DreamError(f"Invalid {label} artifact: expected JSON object.")
        return value

    def _git_visible_paths(self) -> list[Path]:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=self.project_root,
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            raise DreamError("Could not enumerate Git-visible release files.")
        paths = [
            (self.project_root / value).resolve()
            for value in result.stdout.splitlines()
            if value.strip()
        ]
        return sorted(path for path in paths if path.is_file())

    def _read_git_state(self) -> GitReleaseState:
        branch = self._git_output(["branch", "--show-current"]) or "detached"
        commit_sha = self._git_output(["rev-parse", "HEAD"])
        status = self._git_output(["status", "--porcelain"], preserve_lines=True)
        return GitReleaseState(
            branch=branch,
            commit_sha=commit_sha,
            status_lines=status.splitlines() if status else [],
        )

    def _git_output(self, args: list[str], *, preserve_lines: bool = False) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.project_root,
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            raise DreamError(f"Git command failed: git {' '.join(args)}")
        return result.stdout.rstrip() if preserve_lines else result.stdout.strip()

    @staticmethod
    def _write_manifest(
        manifest: LeadershipReleaseManifest,
        output_dir: Path,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "leadership-release-manifest.json").write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        lines = [
            "# DREAM Leadership Release Manifest",
            "",
            f"Release: `{manifest.release_id}`  ",
            f"Status: **{manifest.status}**  ",
            f"Branch/commit: `{manifest.branch}` / `{manifest.commit_sha}`  ",
            f"Source snapshot: `{manifest.source_snapshot_sha256}`",
            "",
            "## Gates",
            "",
            f"- Preflight ready: `{manifest.preflight_ready}`",
            f"- Rehearsal passed/restored: `{manifest.rehearsal_passed}` / "
            f"`{manifest.rehearsal_baseline_restored}`",
            f"- External writes: `{manifest.rehearsal_external_writes_performed}`",
            f"- Benchmark tier/repetitions: `{manifest.benchmark_evidence_tier}` / "
            f"`{manifest.benchmark_repetitions}`",
            f"- Frontend bundle: `{manifest.frontend_bundle_file_count}` files / "
            f"`{manifest.frontend_bundle_sha256}`",
            "",
            "## Warnings",
            "",
            *(f"- {item}" for item in manifest.warnings or ["None."]),
            "",
        ]
        (output_dir / "leadership-release-manifest.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )


class LeadershipReleaseVerifier:
    def __init__(self, *, project_root: Path = PROJECT_ROOT) -> None:
        self.project_root = project_root.resolve()

    def verify(self, manifest_path: Path) -> ReleaseVerificationReport:
        manifest = LeadershipReleaseManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        builder = LeadershipReleaseBuilder(project_root=self.project_root)
        git_state = builder._read_git_state()
        source_paths = builder._git_visible_paths()
        checks = {
            "branch": git_state.branch == manifest.branch,
            "commit": git_state.commit_sha == manifest.commit_sha,
            "git_status": git_state.status_lines == manifest.git_status_lines,
            "source_snapshot": (
                _hash_path_set(self.project_root, source_paths)
                == manifest.source_snapshot_sha256
            ),
            "critical_sources": all(
                _checksum_matches(self.project_root, item)
                for item in manifest.critical_source_checksums
            ),
            "evidence_artifacts": all(
                _checksum_matches(self.project_root, item)
                for item in manifest.evidence_artifact_checksums
            ),
        }
        frontend_dir = self.project_root / "frontend/dist/frontend/browser"
        frontend_paths = sorted(path for path in frontend_dir.rglob("*") if path.is_file())
        checks["frontend_bundle"] = (
            len(frontend_paths) == manifest.frontend_bundle_file_count
            and _hash_path_set(self.project_root, frontend_paths)
            == manifest.frontend_bundle_sha256
        )
        if manifest.status == "frozen":
            checks["frozen_clean_tree"] = not git_state.dirty
        failures = [name for name, passed in checks.items() if not passed]
        return ReleaseVerificationReport(
            verified_at=datetime.now(UTC).isoformat(),
            passed=not failures,
            release_id=manifest.release_id,
            status=manifest.status,
            checks=checks,
            failures=failures,
        )


def _checksum(project_root: Path, path: Path) -> FileChecksum:
    resolved = path.resolve()
    if not resolved.is_relative_to(project_root.resolve()) or not resolved.is_file():
        raise DreamError(f"Release file is missing or outside project root: {path}")
    data = resolved.read_bytes()
    return FileChecksum(
        path=resolved.relative_to(project_root.resolve()).as_posix(),
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
    )


def _checksum_matches(project_root: Path, expected: FileChecksum) -> bool:
    try:
        actual = _checksum(project_root, project_root / expected.path)
    except (DreamError, OSError):
        return False
    return actual.sha256 == expected.sha256 and actual.size_bytes == expected.size_bytes


def _hash_path_set(project_root: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    root = project_root.resolve()
    for path in sorted(paths):
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise DreamError(f"Snapshot path is missing or outside project root: {path}")
        relative = resolved.relative_to(root).as_posix()
        data = resolved.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()
