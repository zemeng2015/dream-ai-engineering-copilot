# SPDX-License-Identifier: Apache-2.0

from uuid import uuid4

from dream.testgen.models import TestGenPlan, TestGenRequest, TestGenResult


class JTestGenAdapter:
    provider_name = "jtestgen"

    def plan(self, request: TestGenRequest) -> TestGenPlan:
        return TestGenPlan(
            run_id=f"jtestgen-plan-{uuid4().hex[:12]}",
            provider_name=self.provider_name,
            target_summary=(
                "JTestGen adapter stub. An external JTestGen CLI could be connected "
                f"for repo_path={request.repo_path} and language={request.target_language}."
            ),
            planned_actions=[
                "Validate repo path and target language.",
                "Build a JTestGen CLI command from TestGenRequest.",
                "Run external tool only when explicitly enabled by future configuration.",
                "Store generated reports under artifacts/ and require human review.",
            ],
            warnings=["Stub only. No external command was executed."],
        )

    def run(self, request: TestGenRequest) -> TestGenResult:
        run_id = f"jtestgen-{uuid4().hex[:12]}"
        markdown = f"""# JTestGen Adapter Stub

Run ID: {run_id}
Provider: {self.provider_name}
Team: {request.team_id}

DREAM MVP does not execute JTestGen. This adapter shows where an external
JTestGen CLI integration can be connected later.

Human review required: true
"""
        return TestGenResult(
            run_id=run_id,
            provider_name=self.provider_name,
            status="stub_not_executed",
            generated_files=[],
            report_markdown=markdown,
            warnings=["JTestGenAdapter is a safe stub. No external command was executed."],
        )
