# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from dream.config import load_config
from dream.context import ContextIntelligenceService
from dream.core.paths import PROJECT_ROOT
from dream.leadership_demo.benchmark import (
    LeadershipBenchmarkFixtureProvider,
    LeadershipBenchmarkSuiteRunner,
    write_benchmark_suite_report,
)
from dream.leadership_demo.service import (
    LEADERSHIP_DEMO_CASE_ID,
    LEADERSHIP_DEMO_PROFILE_ID,
    LEADERSHIP_DEMO_REPO_NAME,
    LEADERSHIP_DEMO_REPO_PATH,
    LEADERSHIP_DEMO_SCAN_ID,
    LEADERSHIP_DEMO_TEAM_ID,
    LeadershipDemoService,
)


class PreflightCheck(BaseModel):
    check_id: str
    status: Literal["pass", "warning", "fail"]
    summary: str
    evidence: list[str] = Field(default_factory=list)


class LeadershipPreflightReport(BaseModel):
    generated_at: str
    ready_for_demo: bool
    branch: str
    scenario_id: str = "leadership-async-status-v1"
    checks: list[PreflightCheck]
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class LeadershipPreflightRunner:
    def __init__(
        self,
        *,
        service: LeadershipDemoService | None = None,
        project_root: Path = PROJECT_ROOT,
    ) -> None:
        self.service = service or LeadershipDemoService()
        self.project_root = project_root

    def run(
        self,
        *,
        output_dir: Path,
        repetitions: int = 3,
        strict_git: bool = False,
        require_frontend_bundle: bool = False,
        branch_name: str | None = None,
        working_tree_dirty: bool | None = None,
    ) -> LeadershipPreflightReport:
        branch = branch_name if branch_name is not None else self._git_branch()
        dirty = (
            working_tree_dirty
            if working_tree_dirty is not None
            else self._git_working_tree_dirty()
        )
        checks = [self._branch_check(branch), self._git_check(dirty, strict_git)]

        seeded = self.service.seed(reset=True)
        snapshot = self.service.requirement_repository.get(seeded.case_id)
        context_service = ContextIntelligenceService(
            requirement_repository=self.service.requirement_repository,
            graph_repository=self.service.graph_repository,
            memory_repository=self.service.memory_repository,
            codebase_repository=self.service.codebase_repository,
        )
        trail = context_service.trace_case(seeded.case_id)
        pack = context_service.assemble_case(seeded.case_id)
        evaluation = self.service.evaluation_repository.get(seeded.evaluation_id)
        audit_records = [
            item
            for item in self.service.audit_repository.list_audit_records()
            if item.case_id == seeded.case_id
        ]
        evaluation_audit = self.service.audit_repository.get_audit_record(
            seeded.evaluation_id
        )

        checks.extend(
            [
                self._scenario_check(seeded),
                self._claim_check(seeded.approved_claim_id, snapshot, trail, pack),
                self._human_gate_check(seeded, snapshot),
                self._source_boundary_check(seeded.source_paths),
                self._trust_artifact_check(
                    seeded,
                    trail,
                    pack,
                    evaluation,
                    audit_records,
                    evaluation_audit,
                ),
                self._provider_profile_check(),
                self._docs_check(),
                self._frontend_check(require_frontend_bundle),
            ]
        )

        suite = LeadershipBenchmarkSuiteRunner(
            provider=LeadershipBenchmarkFixtureProvider(),
            evidence_tier="harness_validation",
        ).run(
            snapshot=snapshot,
            profile_id=LEADERSHIP_DEMO_PROFILE_ID,
            repetitions=repetitions,
        )
        suite_paths = write_benchmark_suite_report(
            suite,
            output_dir=output_dir / "benchmark",
        )
        checks.append(self._benchmark_check(suite, suite_paths))

        failures = [item.summary for item in checks if item.status == "fail"]
        warnings = [item.summary for item in checks if item.status == "warning"]
        next_actions = []
        if dirty:
            next_actions.append("Commit or intentionally stage the reviewed demo snapshot.")
        if suite.sme_reference_proof is None:
            next_actions.append(
                "Obtain an approved, hash-verified SME reference before claiming edit distance."
            )
        if suite.pricing_proof is None:
            next_actions.append(
                "Approve an exact provider/model pricing manifest before citing cost."
            )
        next_actions.append(
            "Run the paired suite on an approved live provider before citing "
            "model-quality evidence."
        )
        report = LeadershipPreflightReport(
            generated_at=datetime.now(UTC).isoformat(),
            ready_for_demo=not failures,
            branch=branch,
            checks=checks,
            failures=failures,
            warnings=warnings,
            next_actions=next_actions,
        )
        self._write_report(report, output_dir)
        return report

    @staticmethod
    def _branch_check(branch: str) -> PreflightCheck:
        normalized = branch.lower()
        if "qwen" in normalized or "champion" in normalized or "hackathon" in normalized:
            return PreflightCheck(
                check_id="product_branch",
                status="fail",
                summary="Leadership preflight is running from a competition branch.",
                evidence=[branch],
            )
        if branch == "main" or "leadership" in normalized:
            status = "pass"
            summary = "Leadership preflight is running from a product branch."
        else:
            status = "warning"
            summary = "Branch is not explicitly identified as main or leadership product."
        return PreflightCheck(
            check_id="product_branch",
            status=status,
            summary=summary,
            evidence=[branch or "detached"],
        )

    @staticmethod
    def _git_check(dirty: bool, strict: bool) -> PreflightCheck:
        if not dirty:
            return PreflightCheck(
                check_id="git_hygiene",
                status="pass",
                summary="Working tree is clean.",
            )
        return PreflightCheck(
            check_id="git_hygiene",
            status="fail" if strict else "warning",
            summary="Working tree has uncommitted changes.",
            evidence=["Use --strict-git for the presentation release gate."],
        )

    @staticmethod
    def _scenario_check(seeded) -> PreflightCheck:
        expected = {
            "team_id": LEADERSHIP_DEMO_TEAM_ID,
            "repo_name": LEADERSHIP_DEMO_REPO_NAME,
            "repo_path": LEADERSHIP_DEMO_REPO_PATH,
            "case_id": LEADERSHIP_DEMO_CASE_ID,
            "scan_id": LEADERSHIP_DEMO_SCAN_ID,
        }
        actual = {key: getattr(seeded, key) for key in expected}
        valid = actual == expected
        return PreflightCheck(
            check_id="fixed_scenario",
            status="pass" if valid else "fail",
            summary=(
                "Fixed DFP scenario identifiers are aligned."
                if valid
                else "Fixed DFP scenario identifiers do not match the leadership contract."
            ),
            evidence=[f"{key}={value}" for key, value in actual.items()],
        )

    @staticmethod
    def _claim_check(claim_id: str, snapshot, trail, pack) -> PreflightCheck:
        evidence_match = any(item.memory_claim_id == claim_id for item in snapshot.evidence)
        trail_match = any(item.claim_id == claim_id for item in trail.memory_claims_used)
        pack_match = any(item.claim_id == claim_id for item in pack.selected_memory_claims)
        reviewer_match = any(
            item.claim_id == claim_id and item.reviewed_by
            for item in trail.memory_claims_used
        )
        valid = all([evidence_match, trail_match, pack_match, reviewer_match])
        return PreflightCheck(
            check_id="approved_claim_consumed",
            status="pass" if valid else "fail",
            summary=(
                "Approved claim is consumed with reviewer proof across generation context."
                if valid
                else (
                    "Approved claim proof is missing from evidence, trail, pack, "
                    "or reviewer metadata."
                )
            ),
            evidence=[
                f"claim_id={claim_id}",
                f"case_evidence={evidence_match}",
                f"context_trail={trail_match}",
                f"context_pack={pack_match}",
                f"reviewer_proof={reviewer_match}",
            ],
        )

    @staticmethod
    def _human_gate_check(seeded, snapshot) -> PreflightCheck:
        open_questions = [item for item in snapshot.questions if item.status == "open"]
        valid = (
            len(open_questions) == 1
            and not seeded.jira_ready
            and snapshot.jira_readiness is not None
            and not snapshot.jira_readiness.ready
        )
        return PreflightCheck(
            check_id="human_gate",
            status="pass" if valid else "fail",
            summary=(
                "Exactly one material question remains open and Jira is blocked."
                if valid
                else "Leadership human-gate state is not deterministic."
            ),
            evidence=[item.question_id for item in open_questions],
        )

    @staticmethod
    def _source_boundary_check(paths: list[str]) -> PreflightCheck:
        forbidden = ["java-demo-repo", "fannie", "hera"]
        violations = [path for path in paths if any(item in path.lower() for item in forbidden)]
        valid = bool(paths) and not violations
        return PreflightCheck(
            check_id="synthetic_source_boundary",
            status="pass" if valid else "fail",
            summary=(
                "Evidence paths stay inside the synthetic DFP leadership boundary."
                if valid
                else "Evidence paths are empty or include a forbidden demo/company identifier."
            ),
            evidence=violations or [f"source_count={len(paths)}"],
        )

    @staticmethod
    def _trust_artifact_check(
        seeded,
        trail,
        pack,
        evaluation,
        audit_records,
        evaluation_audit,
    ) -> PreflightCheck:
        valid = all(
            [
                trail.trail_id == seeded.context_trail_id,
                pack.selected_evidence_count > 0,
                evaluation is not None,
                bool(seeded.evaluation_id),
                bool(audit_records),
                evaluation_audit is not None,
            ]
        )
        return PreflightCheck(
            check_id="trust_artifacts",
            status="pass" if valid else "fail",
            summary=(
                "Context Trail, Context Pack, Eval, and Audit-linked ids are available."
                if valid
                else "One or more trust artifacts are missing."
            ),
            evidence=[
                f"trail={trail.trail_id}",
                f"context_pack={pack.context_pack_id}",
                f"evaluation={seeded.evaluation_id}",
                f"case_audit_records={len(audit_records)}",
                f"evaluation_audit={evaluation_audit is not None}",
            ],
        )

    def _provider_profile_check(self) -> PreflightCheck:
        path = self.project_root / "frontend/src/app/core/product-profile.ts"
        config_path = self.project_root / "dream.yaml"
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        default_provider = (
            load_config(config_path).llm.provider if config_path.exists() else "missing"
        )
        valid = all(
            value in content
            for value in [
                "generationProvider: 'config'",
                "judgeProvider: 'none'",
                "generationProvider: 'qwen-cloud'",
                "judgeProvider: 'qwen-cloud'",
            ]
        ) and default_provider == "mock"
        return PreflightCheck(
            check_id="provider_profile_isolation",
            status="pass" if valid else "fail",
            summary=(
                "Leadership uses the safe backend config selector while Hackathon remains "
                "Qwen-only."
                if valid
                else "Provider profile isolation or the checked-in mock default is missing."
            ),
            evidence=[
                path.as_posix(),
                config_path.as_posix(),
                f"checked_in_default_provider={default_provider}",
            ],
        )

    def _docs_check(self) -> PreflightCheck:
        required = [
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
            "docs/current-development-handoff.md",
        ]
        missing = [value for value in required if not (self.project_root / value).exists()]
        return PreflightCheck(
            check_id="leadership_docs",
            status="pass" if not missing else "fail",
            summary=(
                "Leadership, evidence, trust-boundary, and Pilot documents are present."
                if not missing
                else "Required leadership documents are missing."
            ),
            evidence=missing or required,
        )

    def _frontend_check(self, required: bool) -> PreflightCheck:
        index = self.project_root / "frontend/dist/frontend/browser/index.html"
        if index.exists():
            return PreflightCheck(
                check_id="frontend_bundle",
                status="pass",
                summary="Angular production bundle is present.",
                evidence=[index.as_posix()],
            )
        return PreflightCheck(
            check_id="frontend_bundle",
            status="fail" if required else "warning",
            summary="Angular production bundle is missing; run npm build before the meeting.",
            evidence=[index.as_posix()],
        )

    @staticmethod
    def _benchmark_check(suite, paths: tuple[Path, Path]) -> PreflightCheck:
        valid = all(
            [
                suite.evidence_tier == "harness_validation",
                suite.repetitions >= 3,
                suite.same_provider_verified,
                suite.same_model_verified,
                suite.same_request_verified,
                suite.same_contract_verified,
                all(run.stateless.parse_error is None for run in suite.runs),
                all(run.dream.parse_error is None for run in suite.runs),
            ]
        )
        return PreflightCheck(
            check_id="paired_benchmark_harness",
            status="pass" if valid else "fail",
            summary=(
                "Three-or-more paired harness repetitions passed integrity checks."
                if valid
                else "Paired benchmark harness integrity checks failed."
            ),
            evidence=[path.as_posix() for path in paths],
        )

    def _git_branch(self) -> str:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.project_root,
            capture_output=True,
            check=False,
            text=True,
        )
        return result.stdout.strip() or "detached"

    def _git_working_tree_dirty(self) -> bool:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.project_root,
            capture_output=True,
            check=False,
            text=True,
        )
        return bool(result.stdout.strip())

    @staticmethod
    def _write_report(report: LeadershipPreflightReport, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "leadership-preflight.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        lines = [
            "# DREAM Leadership Preflight",
            "",
            f"Ready for demo: **{report.ready_for_demo}**  ",
            f"Branch: `{report.branch}`  ",
            f"Generated: `{report.generated_at}`",
            "",
            "| Check | Status | Summary |",
            "|---|---|---|",
            *(
                f"| {item.check_id} | {item.status} | {item.summary} |"
                for item in report.checks
            ),
            "",
            "## Next actions",
            "",
            *(f"- {item}" for item in report.next_actions),
            "",
        ]
        (output_dir / "leadership-preflight.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )
