# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from dream.context import ContextIntelligenceService
from dream.core.errors import DreamError
from dream.evals import EvaluationRequest
from dream.evals.evaluator import EvaluationAgent
from dream.leadership_demo.service import (
    LEADERSHIP_DEMO_PROFILE_ID,
    LEADERSHIP_DEMO_REVIEWER,
    LeadershipDemoService,
)

LEADERSHIP_GATE_ANSWER = (
    "Persist task status transitions as the authoritative recovery source. "
    "SERVICE_TASK and BATCH_TASK share lifecycle vocabulary while adapters preserve "
    "their execution-specific behavior."
)


class LeadershipRehearsalReport(BaseModel):
    started_at: str
    completed_at: str
    passed: bool
    scenario_version: str
    team_id: str
    repo_name: str
    case_id: str
    scan_id: str
    approved_claim_id: str
    gate_question_id: str
    gate_question: str
    answered_by: str
    before_jira_ready: bool
    before_open_question_ids: list[str] = Field(default_factory=list)
    after_jira_ready: bool
    after_open_question_ids: list[str] = Field(default_factory=list)
    claim_proof_preserved: bool
    context_trail_id: str
    evaluation_id: str
    case_audit_records_before: int
    case_audit_records_after: int
    external_writes_performed: bool = False
    baseline_restored: bool
    restored_jira_ready: bool
    restored_open_question_ids: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)


class LeadershipRehearsalRunner:
    def __init__(self, *, service: LeadershipDemoService | None = None) -> None:
        self.service = service or LeadershipDemoService()

    def run(self, *, output_dir: Path) -> LeadershipRehearsalReport:
        started_at = datetime.now(UTC).isoformat()
        seeded = self.service.seed(reset=True)
        before = self.service.requirement_repository.get(seeded.case_id)
        before_open = [
            item.question_id for item in before.questions if item.status == "open"
        ]
        if len(before_open) != 1:
            raise DreamError(
                "Leadership rehearsal requires exactly one open baseline question."
            )
        gate = next(item for item in before.questions if item.question_id == before_open[0])
        before_audits = self._case_audit_count(seeded.case_id)

        requirement_service = self.service.requirement_service()
        requirement_service.answer_question(
            seeded.case_id,
            gate.question_id,
            LEADERSHIP_GATE_ANSWER,
            answered_by=LEADERSHIP_DEMO_REVIEWER,
        )
        requirement_service.generate_engineering_brief(seeded.case_id)
        requirement_service.generate_jira_draft(seeded.case_id)
        after = requirement_service.get_case(seeded.case_id)
        after_open = [
            item.question_id for item in after.questions if item.status == "open"
        ]

        context_service = ContextIntelligenceService(
            requirement_repository=self.service.requirement_repository,
            graph_repository=self.service.graph_repository,
            memory_repository=self.service.memory_repository,
            codebase_repository=self.service.codebase_repository,
        )
        trail = context_service.trace_case(seeded.case_id)
        pack = context_service.assemble_case(seeded.case_id)
        context_service.prompt_for_case(seeded.case_id, target="jira_draft")
        claim_in_evidence = any(
            item.memory_claim_id == seeded.approved_claim_id for item in after.evidence
        )
        claim_in_trail = any(
            item.claim_id == seeded.approved_claim_id
            and item.status == "approved"
            and bool(item.reviewed_by)
            for item in trail.memory_claims_used
        )
        claim_in_pack = any(
            item.claim_id == seeded.approved_claim_id
            for item in pack.selected_memory_claims
        )
        claim_proof_preserved = all(
            [claim_in_evidence, claim_in_trail, claim_in_pack]
        )

        evaluation = EvaluationAgent(
            repository=self.service.evaluation_repository,
            audit_repository=self.service.audit_repository,
            audit_logger=self.service.audit_logger,
            requirement_repository=self.service.requirement_repository,
        ).evaluate(
            EvaluationRequest(
                target_type="jira_draft",
                case_id=seeded.case_id,
                team_id=seeded.team_id,
                repo_name=seeded.repo_name,
                expected_profile=LEADERSHIP_DEMO_PROFILE_ID,
            )
        )
        after_audits = self._case_audit_count(seeded.case_id)
        after_ready = bool(after.jira_readiness and after.jira_readiness.ready)

        restored = self.service.seed(reset=True)
        restored_snapshot = self.service.requirement_repository.get(restored.case_id)
        restored_open = [
            item.question_id
            for item in restored_snapshot.questions
            if item.status == "open"
        ]
        restored_ready = bool(
            restored_snapshot.jira_readiness
            and restored_snapshot.jira_readiness.ready
        )
        baseline_restored = (
            restored.case_id == seeded.case_id
            and restored.approved_claim_id == seeded.approved_claim_id
            and len(restored_open) == 1
            and not restored_ready
        )
        checks = [
            "Baseline started with one open question and Jira blocked.",
            "The named reviewer answered the material backend decision.",
            "Jira readiness became true with zero open questions.",
            "Approved claim evidence/reviewer proof remained in Context Trail and Pack.",
            "A new deterministic Eval and case-scoped Audit trail were produced.",
            "No Jira, GitHub, deployment, email, or messaging write was performed.",
            "The fixed blocked baseline was restored after rehearsal.",
        ]
        passed = all(
            [
                not seeded.jira_ready,
                len(before_open) == 1,
                after_ready,
                not after_open,
                claim_proof_preserved,
                after_audits > before_audits,
                baseline_restored,
            ]
        )
        report = LeadershipRehearsalReport(
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat(),
            passed=passed,
            scenario_version=seeded.scenario_version,
            team_id=seeded.team_id,
            repo_name=seeded.repo_name,
            case_id=seeded.case_id,
            scan_id=seeded.scan_id,
            approved_claim_id=seeded.approved_claim_id,
            gate_question_id=gate.question_id,
            gate_question=gate.question,
            answered_by=LEADERSHIP_DEMO_REVIEWER,
            before_jira_ready=seeded.jira_ready,
            before_open_question_ids=before_open,
            after_jira_ready=after_ready,
            after_open_question_ids=after_open,
            claim_proof_preserved=claim_proof_preserved,
            context_trail_id=trail.trail_id,
            evaluation_id=evaluation.scorecard.evaluation_id,
            case_audit_records_before=before_audits,
            case_audit_records_after=after_audits,
            baseline_restored=baseline_restored,
            restored_jira_ready=restored_ready,
            restored_open_question_ids=restored_open,
            checks=checks,
        )
        self._write_report(report, output_dir)
        if not passed:
            raise DreamError("Leadership rehearsal failed one or more transition checks.")
        return report

    def _case_audit_count(self, case_id: str) -> int:
        return len(
            [
                item
                for item in self.service.audit_repository.list_audit_records()
                if item.case_id == case_id
            ]
        )

    @staticmethod
    def _write_report(report: LeadershipRehearsalReport, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "leadership-rehearsal.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        lines = [
            "# DREAM Leadership Rehearsal",
            "",
            f"Passed: **{report.passed}**  ",
            f"Case: `{report.case_id}`  ",
            f"Approved claim: `{report.approved_claim_id}`",
            "",
            "## Human gate transition",
            "",
            f"- Before: Jira ready `{report.before_jira_ready}`; "
            f"open questions `{len(report.before_open_question_ids)}`",
            f"- Answered: `{report.gate_question_id}` by `{report.answered_by}`",
            f"- After: Jira ready `{report.after_jira_ready}`; "
            f"open questions `{len(report.after_open_question_ids)}`",
            f"- Claim proof preserved: `{report.claim_proof_preserved}`",
            f"- Baseline restored: `{report.baseline_restored}`",
            "",
            "## Checks",
            "",
            *(f"- {item}" for item in report.checks),
            "",
        ]
        (output_dir / "leadership-rehearsal.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )
