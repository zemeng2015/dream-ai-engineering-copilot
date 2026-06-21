# SPDX-License-Identifier: Apache-2.0

import hashlib

from dream.requirement_cases.models import (
    ClarificationQuestion,
    ContextEvidence,
    RequirementCase,
)

QUESTION_BANK = {
    "BA": [
        (
            "Which user-visible status labels should be exposed for this request?",
            "Business language must match what users and support teams can understand.",
        ),
        (
            "What acceptance criteria define a successful long-running job status flow?",
            "Engineering and QA need a shared definition of done before implementation.",
        ),
    ],
    "TL": [
        (
            "Should status tracking be handled inside the existing service or behind "
            "a new boundary?",
            "This affects scope, ownership, coupling, and future extensibility.",
        ),
        (
            "Which existing components are in scope for the first release?",
            "A narrow scope keeps implementation reviewable and reduces regression risk.",
        ),
    ],
    "FE": [
        (
            "Should the UI poll, refresh manually, or subscribe to async status updates?",
            "The interaction model changes API expectations and user feedback timing.",
        ),
        (
            "What error and empty-state messages should users see for missing or failed jobs?",
            "Clear state messaging reduces support ambiguity.",
        ),
    ],
    "BE": [
        (
            "What exact status transitions are allowed for submitted, running, completed, "
            "and failed jobs?",
            "The backend needs deterministic transition rules and test coverage.",
        ),
        (
            "Does status need persistence beyond the current in-memory demo tracker?",
            "Persistence changes data design, recovery behavior, and operational support.",
        ),
    ],
    "QA": [
        (
            "Which regression scenarios must cover async status tracking?",
            "QA needs success, failure, missing job, retry, and timeout scenarios.",
        ),
        (
            "What test data is required to simulate completed and failed long-running jobs?",
            "Reusable data setup makes manual and automated validation repeatable.",
        ),
    ],
    "OPS": [
        (
            "What monitoring signal should indicate a stuck or failed long-running job?",
            "Operations needs actionable diagnostics before support escalation.",
        ),
        (
            "Should the runbook define retry, timeout, and failure triage steps?",
            "Operational guidance avoids ad hoc incident handling.",
        ),
    ],
    "SECURITY": [
        (
            "Could status responses expose sensitive request or result data?",
            "Status APIs should avoid leaking user or operational details.",
        )
    ],
}


class QuestionGenerator:
    def generate(
        self,
        case: RequirementCase,
        evidence: list[ContextEvidence],
        *,
        role: str | None = None,
    ) -> list[ClarificationQuestion]:
        roles = [role.upper()] if role else ["BA", "TL", "FE", "BE", "QA", "OPS", "SECURITY"]
        sources = sorted({item.source_path for item in evidence})[:5]
        questions: list[ClarificationQuestion] = []
        for target_role in roles:
            for question, why in QUESTION_BANK.get(target_role, []):
                questions.append(
                    ClarificationQuestion(
                        question_id=self._stable_id(f"{case.case_id}:{target_role}:{question}"),
                        case_id=case.case_id,
                        target_role=target_role,
                        question=question,
                        why_it_matters=why,
                        related_sources=sources,
                    )
                )
        return questions

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
