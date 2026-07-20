# SPDX-License-Identifier: Apache-2.0

import json

from dream.llm import LLMResponse, OpenAIResponsesProvider
from dream.testgen import JTestGenAdapter, TestGenRequest
from dream.workflow import EngineeringLoopRequest, EngineeringLoopService


class BuildWeekFakeProvider:
    provider_name = "openai-responses"
    model_name = "gpt-5.6-sol"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete(self, prompt):
        value = prompt.prompt if hasattr(prompt, "prompt") else str(prompt)
        self.prompts.append(value)
        if "Generate focused JUnit 5 unit tests" in value:
            text = json.dumps(
                {
                    "tests": [
                        {
                            "path": (
                                "src/test/java/com/democorp/demo/"
                                "JobExecutionServiceGeneratedTest.java"
                            ),
                            "content": """package com.democorp.demo;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JobExecutionServiceGeneratedTest {
    @Test
    void generatedCandidateRequiresReview() {
        assertTrue(true);
    }
}
""",
                            "rationale": "Covers the newly changed service boundary.",
                        }
                    ]
                }
            )
        elif "PR review" in value or "unified diff" in value.lower():
            text = """# PR Review Summary

## Changed Files
- `src/main/java/com/democorp/demo/JobExecutionService.java`

## Findings
- Verify terminal states and regression behavior against codebase memory.

## Test Strategy
- Run `JobExecutionServiceTest.java` and add failure-path tests.

## Sources Used
- src/main/java/com/democorp/demo/JobExecutionService.java

Human review required before merge.
"""
        else:
            text = """# Jira Story Draft

## User Story
As an operator, I need governed async status tracking.

## Acceptance Criteria
- GIVEN a submitted job WHEN status changes THEN expose the current state.
- Preserve existing behavior and require human approval for external actions.

## Test Scenarios
- Test RUNNING, COMPLETED, and FAILED transitions.

## Open Questions
- Confirm polling interval with OPS.

## Sources Used
- src/main/java/com/democorp/demo/JobExecutionService.java
"""
        return LLMResponse(
            text=text,
            model_name=self.model_name,
            provider_name=self.provider_name,
            token_usage={"input_tokens": 10, "output_tokens": 20},
        )


def test_openai_responses_extracts_nested_output_text() -> None:
    payload = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "hello GPT-5.6"}],
            }
        ]
    }
    assert OpenAIResponsesProvider._extract_output_text(payload) == "hello GPT-5.6"


def test_jtestgen_generates_isolated_review_artifact() -> None:
    result = JTestGenAdapter(llm_provider=BuildWeekFakeProvider()).run(
        TestGenRequest(
            team_id="demo_team",
            repo_path="examples/java-demo-repo",
            target_files=[
                "src/main/java/com/democorp/demo/JobExecutionService.java"
            ],
            dry_run=False,
        )
    )

    assert result.status == "generated_needs_review"
    assert result.model_name == "gpt-5.6-sol"
    assert len(result.generated_files) == 1
    assert result.generated_files[0].startswith("artifacts/jtestgen/")
    assert "No files were modified in the target repository" in result.report_markdown


def test_engineering_loop_connects_all_five_stages() -> None:
    provider = BuildWeekFakeProvider()
    result = EngineeringLoopService(llm_provider=provider).run(
        EngineeringLoopRequest(
            raw_request=(
                "Add governed async status visibility while preserving existing behavior, "
                "requiring source-backed Jira drafting, PR review, JUnit generation, and eval."
            ),
            target_files=[
                "src/main/java/com/democorp/demo/JobExecutionService.java"
            ],
            run_llm_judge=False,
        )
    )

    assert [stage.stage for stage in result.stages] == [
        "memory",
        "jira",
        "pr_review",
        "testgen",
        "eval",
    ]
    assert result.evidence_count > 0
    assert result.generated_test_files
    assert result.markdown_path.startswith("artifacts/engineering-loop/")
    assert "Codex + GPT-5.6" in result.summary_markdown
    testgen_prompt = next(
        prompt for prompt in provider.prompts if "Generate focused JUnit 5 unit tests" in prompt
    )
    assert "ORIGINAL CHANGE REQUEST" in testgen_prompt
    assert "GOVERNED JIRA DRAFT" in testgen_prompt
