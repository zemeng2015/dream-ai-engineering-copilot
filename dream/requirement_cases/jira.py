# SPDX-License-Identifier: Apache-2.0

from dream.dlp import ensure_dlp_guarded_provider
from dream.llm import BaseLLMProvider
from dream.llm.base import LLMRequest
from dream.requirement_cases.models import JiraDraft, JiraDraftContext, RequirementCaseSnapshot
from dream.requirement_cases.templates import render_jira_draft, render_jira_draft_prompt


class JiraDraftGenerator:
    def __init__(self, *, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = (
            ensure_dlp_guarded_provider(llm_provider) if llm_provider is not None else None
        )
        self.last_model_provider = "deterministic"
        self.last_model_name = "jira-draft-v1"

    def generate(self, snapshot: RequirementCaseSnapshot) -> JiraDraft:
        context = self.prepare(snapshot)
        markdown = context.deterministic_markdown
        if self.llm_provider is not None:
            response = self.llm_provider.complete(
                LLMRequest(
                    prompt=context.prompt,
                    metadata={
                        "team_id": snapshot.case.team_id,
                        "resource_id": snapshot.case.case_id,
                        "use_case": "jira_draft",
                        "classification": snapshot.case.access.classification,
                    },
                )
            )
            markdown = response.text
            self.last_model_provider = response.provider_name
            self.last_model_name = response.model_name
        else:
            self.last_model_provider = "deterministic"
            self.last_model_name = "jira-draft-v1"
        return JiraDraft(
            case_id=snapshot.case.case_id,
            markdown=markdown,
            sources_used=context.sources_used,
            warnings=context.warnings,
        )

    def prepare(self, snapshot: RequirementCaseSnapshot) -> JiraDraftContext:
        deterministic_markdown = render_jira_draft(
            case=snapshot.case,
            evidence=snapshot.evidence,
            impact_items=snapshot.impact_items,
            questions=snapshot.questions,
        )
        prompt = render_jira_draft_prompt(
            case=snapshot.case,
            evidence=snapshot.evidence,
            impact_items=snapshot.impact_items,
            questions=snapshot.questions,
            deterministic_draft=deterministic_markdown,
        )
        sources = sorted({path for item in snapshot.evidence for path in item.provenance_paths()})
        warnings = [] if snapshot.evidence else ["No evidence was available for this Jira draft."]
        return JiraDraftContext(
            case_id=snapshot.case.case_id,
            deterministic_markdown=deterministic_markdown,
            prompt=prompt,
            prompt_char_count=len(prompt),
            deterministic_char_count=len(deterministic_markdown),
            sources_used=sources,
            warnings=warnings,
        )
