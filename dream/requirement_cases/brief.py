# SPDX-License-Identifier: Apache-2.0

from dream.llm import BaseLLMProvider
from dream.requirement_cases.models import EngineeringBrief, RequirementCaseSnapshot
from dream.requirement_cases.templates import (
    render_engineering_brief,
    render_engineering_brief_prompt,
)


class EngineeringBriefGenerator:
    def __init__(self, *, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = llm_provider
        self.last_model_provider = "deterministic"
        self.last_model_name = "engineering-brief-v1"

    def generate(self, snapshot: RequirementCaseSnapshot) -> EngineeringBrief:
        deterministic_markdown = render_engineering_brief(
            case=snapshot.case,
            evidence=snapshot.evidence,
            impact_items=snapshot.impact_items,
            questions=snapshot.questions,
        )
        markdown = deterministic_markdown
        if self.llm_provider is not None:
            prompt = render_engineering_brief_prompt(
                case=snapshot.case,
                evidence=snapshot.evidence,
                impact_items=snapshot.impact_items,
                questions=snapshot.questions,
                deterministic_draft=deterministic_markdown,
            )
            response = self.llm_provider.complete(prompt)
            markdown = response.text
            self.last_model_provider = response.provider_name
            self.last_model_name = response.model_name
        else:
            self.last_model_provider = "deterministic"
            self.last_model_name = "engineering-brief-v1"
        sources = sorted({item.source_path for item in snapshot.evidence})
        warnings = [] if snapshot.evidence else ["No evidence was available for this brief."]
        return EngineeringBrief(
            case_id=snapshot.case.case_id,
            markdown=markdown,
            sources_used=sources,
            warnings=warnings,
        )
