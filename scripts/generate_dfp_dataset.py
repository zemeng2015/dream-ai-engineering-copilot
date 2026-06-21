# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "knowledge_packs" / "demo_team"
DOCS = PACK / "docs"
EXAMPLES = ROOT / "examples"
DFP = EXAMPLES / "dfp-demo-repo"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dedent(content).strip()
    if path.suffix.lower() == ".md":
        normalized_lines = []
        for line in text.splitlines():
            while line.startswith("        "):
                line = line[8:]
            normalized_lines.append(line)
        text = "\n".join(normalized_lines)
    path.write_text(text + "\n", encoding="utf-8")


def fm(
    title: str,
    doc_type: str,
    component: str,
    concepts: list[str],
    *,
    code: list[str] | None = None,
    jira: list[str] | None = None,
    prs: list[str] | None = None,
    incidents: list[str] | None = None,
) -> str:
    def block(name: str, values: list[str] | None) -> list[str]:
        if not values:
            return []
        return [f"{name}:"] + [f"  - {value}" for value in values]

    lines = [
        "---",
        f"title: {json.dumps(title)}",
        f"doc_type: {json.dumps(doc_type)}",
        'team_id: "demo_team"',
        'app: "ForecastDemo"',
        f"component: {json.dumps(component)}",
        "concepts:",
        *[f"  - {concept}" for concept in concepts],
        *block("related_code", code),
        *block("related_jira", jira),
        *block("related_pr", prs),
        *block("related_incidents", incidents),
        "---",
        "",
    ]
    return "\n".join(lines)


def bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- None"


def section_doc(
    *,
    title: str,
    doc_type: str,
    component: str,
    concepts: list[str],
    purpose: str,
    context: str,
    behaviors: list[str],
    affected: list[str],
    failures: list[str],
    tests: list[str],
    related_docs: list[str],
    code: list[str],
    jira: list[str],
    prs: list[str],
    incidents: list[str],
    notes: str,
) -> str:
    return (
        fm(title, doc_type, component, concepts, code=code, jira=jira, prs=prs, incidents=incidents)
        + f"""
        # {title}

        ## Purpose
        {purpose}

        ## Domain Context
        {context}

        ## Key Behaviors
        {bullet(behaviors)}

        ## Affected Components
        {bullet(affected)}

        ## Failure Modes
        {bullet(failures)}

        ## Test Considerations
        {bullet(tests)}

        ## Related Docs
        {bullet(related_docs)}

        ## Related Fake Code Files
        {bullet(code)}

        ## Related Fake Jira
        {bullet(jira)}

        ## Related Fake PRs
        {bullet(prs)}

        ## Related Fake Incidents
        {bullet(incidents)}

        ## Open Questions Or Review Notes
        {notes}
        """
    )


def build_team_yaml() -> None:
    write(
        PACK / "team.yaml",
        """
        # SPDX-License-Identifier: Apache-2.0

        team_name: Demo Forecast Team
        team_id: demo_team
        applications:
          - ForecastDemo
          - BatchJobDemo
          - OutputPreviewDemo
        repositories:
          - dfp-demo-repo
        document_paths:
          - docs/domain
          - docs/architecture
          - docs/runbooks
          - docs/incidents
          - docs/historical-jira
          - docs/historical-pr
          - docs/testing
          - docs/pr-review
          - docs/concepts
        review_rules:
          - Check requirement alignment with Job, Workflow, Task, and Execution concepts.
          - Check whether async status transitions are fully defined.
          - Check whether SERVICE_TASK and BATCH_TASK behavior differs.
          - Check missing tests for status transitions.
          - Check output collection idempotency.
          - Check large file preview behavior.
          - Check partial completion behavior.
          - Check operator runbook impact.
          - Check UI polling and error state behavior.
          - Check audit logging for execution state changes.
        requirement_template: engineering_brief
        test_generation_rules:
          provider: mock
          human_review_required: true
        roles:
          - BA
          - TL
          - FE
          - BE
          - QA
          - OPS
        """,
    )


def build_knowledge_docs() -> None:
    common_code = [
        "backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java",
        "backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java",
        "frontend/src/app/execution/execution-monitor.component.ts",
    ]
    domain = [
        (
            "glossary.md",
            "DFP Glossary",
            "domain-model",
            ["Job", "Workflow", "Task", "Execution"],
            "Defines the core DemoCorp Forecast Platform vocabulary used across requirements, code reviews, runbooks, Jira history, incidents, and fake code.",
            "DFP is a synthetic forecast platform where Analysts create Jobs, select versioned Workflows, upload task-level files, execute Workflows, monitor asynchronous Execution status, preview outputs, and download results.",
            [
                "Job is the analyst-created forecast case with name, owner, workflow, status, createdAt, and updatedAt.",
                "Workflow is a versioned ordered graph of Tasks with dependencies, execution type, and output expectations.",
                "Task is SERVICE_TASK or BATCH_TASK.",
                "Execution is a run instance with status, timestamps, task executions, and output artifacts.",
            ],
            ["DFP-101", "DFP-106", "DFP-110"],
            ["PR-502", "PR-509", "PR-508"],
            ["INC-103", "INC-105", "INC-102"],
        ),
        (
            "job-lifecycle.md",
            "Job Execution Lifecycle",
            "job-lifecycle",
            ["job execution", "execution status", "analyst workflow"],
            "Explains the analyst path from Job creation to output download.",
            "A Job starts as a forecast case, binds to a Workflow version, receives task-level config and input files, creates an Execution, and collects output artifacts.",
            [
                "Only one active RUNNING Execution is allowed per Job in the demo rules.",
                "Execution starts QUEUED and moves through RUNNING to a terminal status.",
                "Job Detail should show latest Execution and output readiness.",
            ],
            ["DFP-101", "DFP-109", "DFP-112"],
            ["PR-502", "PR-510"],
            ["INC-103", "INC-105"],
        ),
        (
            "workflow-model.md",
            "Workflow Model",
            "workflow-model",
            ["workflow", "workflow versioning", "task dependencies"],
            "Defines Admin-managed Workflow versions and task dependency behavior.",
            "A Workflow is a versioned list of Task definitions. Published versions are immutable once used by Jobs.",
            [
                "Workflow versions are immutable after publication.",
                "Task dependencies control orchestration order.",
                "Output expectations guide OutputCollector completeness checks.",
            ],
            ["DFP-105", "DFP-108"],
            ["PR-507"],
            ["INC-105"],
        ),
        (
            "task-model.md",
            "Task Model",
            "task-model",
            ["Task", "SERVICE_TASK", "BATCH_TASK", "task config validation"],
            "Describes task definitions, SERVICE_TASK and BATCH_TASK behavior, and task-level config.",
            "SERVICE_TASK entries run lightweight functions. BATCH_TASK entries run longer batch-style processing and require timeout, retry, and Operator visibility.",
            [
                "TaskDefinition declares task id, display name, type, dependencies, timeout, retry policy, required inputs, and required config fields.",
                "SERVICE_TASK should fail fast with user-safe errors.",
                "BATCH_TASK should expose retry and timeout status.",
            ],
            ["DFP-102", "DFP-107", "DFP-111"],
            ["PR-501", "PR-506"],
            ["INC-101", "INC-106"],
        ),
        (
            "execution-model.md",
            "Execution Model",
            "execution-model",
            ["Execution", "execution status", "task status", "partial success"],
            "Defines Execution and TaskExecution status behavior across UI, backend, orchestration, and processors.",
            "Execution is a run instance of a Job. TaskExecution records provide task-level progress, retry, failure, skipped, and completion signals.",
            [
                "Execution statuses are QUEUED, RUNNING, FAILED, COMPLETED, CANCELLED, and PARTIAL_SUCCESS.",
                "Task statuses are PENDING, QUEUED, RUNNING, FAILED, COMPLETED, SKIPPED, and RETRYING.",
                "PARTIAL_SUCCESS requires explicit optional-task rules.",
            ],
            ["DFP-101", "DFP-106", "DFP-109"],
            ["PR-505", "PR-509"],
            ["INC-103", "INC-105"],
        ),
        (
            "user-roles.md",
            "DFP User Roles",
            "roles",
            ["Analyst", "Operator", "Admin", "role-specific questions"],
            "Captures business and engineering roles used by Requirement Case analysis.",
            "DFP features create knowledge asymmetry across Analyst, Operator, Admin, BA, TL, FE, BE, QA, and OPS.",
            [
                "Analyst creates Jobs, uploads task inputs, executes Jobs, monitors status, previews outputs, and downloads results.",
                "Operator investigates failed, stuck, or partially complete Executions.",
                "Admin manages Workflow versions and Task definitions.",
            ],
            ["DFP-109", "DFP-111"],
            ["PR-502", "PR-510"],
            ["INC-103", "INC-108"],
        ),
        (
            "data-artifact-model.md",
            "Data Artifact Model",
            "output-artifacts",
            ["output artifacts", "object storage", "preview", "download"],
            "Defines output artifact metadata for forecast results.",
            "Output artifacts reference S3-like object storage and can be previewed directly or through Athena-like query preview.",
            [
                "OutputArtifact includes execution id, task id, artifact key, content type, row count, size, checksum, preview mode, and idempotency key.",
                "OutputCollector writes metadata after task completion and final execution completion.",
                "OutputPreviewService chooses direct preview or Athena-style preview.",
            ],
            ["DFP-103", "DFP-104", "DFP-110"],
            ["PR-503", "PR-504", "PR-508"],
            ["INC-102", "INC-104", "INC-107", "INC-108"],
        ),
    ]
    for name, title, component, concepts, purpose, context, behaviors, jira, prs, incidents in domain:
        write(
            DOCS / "domain" / name,
            section_doc(
                title=title,
                doc_type="domain",
                component=component,
                concepts=concepts,
                purpose=purpose,
                context=context,
                behaviors=behaviors,
                affected=[
                    "Job List Page",
                    "Job Detail Page",
                    "Execution Monitor",
                    "Java backend domain models",
                    "AWS-style orchestration",
                    "Python processors",
                ],
                failures=[
                    "Status values drift between UI and backend.",
                    "Retry behavior produces duplicate outputs.",
                    "Invalid config fails late at execution time.",
                    "Partial completion behavior is not defined.",
                ],
                tests=[
                    "Cover status transition matrix.",
                    "Cover SERVICE_TASK and BATCH_TASK routing.",
                    "Cover idempotent output collection.",
                    "Cover linked fake incidents as regressions.",
                ],
                related_docs=["status-tracking-design.md", "output-collection-design.md"],
                code=common_code,
                jira=jira,
                prs=prs,
                incidents=incidents,
                notes="Do not accept vague requirements unless they map back to Job, Workflow, Task, Execution, and role-specific behavior.",
            ),
        )

    architecture = [
        ("architecture-overview.md", "Architecture Overview", "platform-architecture", ["UI", "Java backend", "AWS orchestration", "Python processors"], "Provides the cross-layer DFP map for Requirement Case impact analysis.", "DFP has Angular-like UI, Spring Boot-like Java backend, AWS-style orchestration, and Python processors."),
        ("ui-architecture.md", "UI Architecture", "ui", ["Execution Monitor", "Output Preview", "Admin Workflow Console"], "Describes the UI surfaces for Analysts, Operators, and Admins.", "The UI is dense and workflow-oriented: Job List, Job Detail, Execution Monitor, Output Preview, and Admin Workflow Console."),
        ("java-backend-architecture.md", "Java Backend Architecture", "backend-api", ["Spring Boot", "REST", "StatusTracker", "OutputCollector"], "Describes controllers, services, domain models, adapters, and collectors.", "Java backend owns API contracts, business decisions, status persistence, output collection, and adapter boundaries."),
        ("aws-orchestration-architecture.md", "AWS Orchestration Architecture", "cloud-orchestration", ["Step Functions", "Lambda", "Batch", "CloudWatch"], "Documents the fake AWS-style orchestration layer.", "Step Functions-like orchestration routes service tasks to Lambda-like handlers and batch tasks to Batch-like runners."),
        ("python-processor-architecture.md", "Python Processor Architecture", "python-processors", ["InputValidator", "ForecastProcessor", "DataTransformer", "OutputAggregator"], "Describes validation, forecast processing, transformation, and aggregation.", "Processors are called from service or batch boundaries and must return structured user-safe errors and output metadata."),
        ("service-vs-batch-task.md", "Service vs Batch Task", "task-routing", ["SERVICE_TASK", "BATCH_TASK", "retry"], "Clarifies behavioral differences between SERVICE_TASK and BATCH_TASK.", "SERVICE_TASK is lightweight and short; BATCH_TASK is long-running, retryable, and operationally visible."),
        ("status-tracking-design.md", "Status Tracking Design", "execution-status", ["execution status", "task status", "async tracking", "polling"], "Defines async Execution and Task status tracking across DFP.", "Analysts need to know which Task is still running; Operators need history for stuck executions; FE needs polling; BE needs legal transitions."),
        ("output-collection-design.md", "Output Collection Design", "output-collection", ["OutputCollector", "idempotency", "object storage"], "Defines output artifact collection and retry idempotency.", "OutputCollector reads manifests, verifies storage metadata, writes OutputArtifact records, and prevents duplicate result files."),
        ("output-preview-design.md", "Output Preview Design", "output-preview", ["output preview", "pagination", "Athena preview"], "Defines small and large output preview behavior.", "Small outputs use direct preview. Large partitioned outputs use Athena-like preview with partition predicates."),
        ("workflow-versioning-design.md", "Workflow Versioning Design", "workflow-versioning", ["workflow versioning", "Admin", "immutability"], "Defines Workflow versioning for Admin-managed changes.", "Published Workflow versions are immutable so historical Jobs and Executions remain reproducible."),
    ]
    for name, title, component, concepts, purpose, context in architecture:
        write(
            DOCS / "architecture" / name,
            section_doc(
                title=title,
                doc_type="architecture",
                component=component,
                concepts=concepts,
                purpose=purpose,
                context=context,
                behaviors=[
                    "Trace business behavior across UI, Java backend, AWS-style orchestration, and Python processors.",
                    "Preserve DFP vocabulary in API contracts and UI messages.",
                    "Update runbooks, tests, and audit behavior when execution semantics change.",
                ],
                affected=[
                    "frontend/src/app/execution/execution-monitor.component.ts",
                    "backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java",
                    "aws/step-functions/job-execution-state-machine.asl.json",
                    "python-processors/processors/input_validator.py",
                ],
                failures=[
                    "UI polling without backend stale detection.",
                    "Backend status changes without runbook updates.",
                    "Output collection without idempotency.",
                    "Processor validation without user-facing errors.",
                ],
                tests=[
                    "Add service tests for backend decisions.",
                    "Add UI state tests for status and preview behavior.",
                    "Add processor tests for validation and output metadata.",
                ],
                related_docs=["execution-model.md", "status-tracking-design.md", "output-collection-design.md"],
                code=common_code,
                jira=["DFP-101", "DFP-109", "DFP-112"],
                prs=["PR-502", "PR-505", "PR-510"],
                incidents=["INC-103", "INC-105"],
                notes="TL review should check which layers change and which layers only need test or documentation updates.",
            ),
        )

    runbooks = [
        ("batch-job-failure-runbook.md", "Batch Job Failure Runbook", "BATCH_TASK exceeded timeout and Execution stayed RUNNING too long.", "Check BatchJobAdapter job id, timeout, retry count, task status, and CloudWatch-like log correlation.", ["INC-101"]),
        ("status-stuck-running-runbook.md", "Status Stuck RUNNING Runbook", "Execution or TaskExecution remains RUNNING after processor completion.", "Compare StatusTracker lastUpdated, orchestration terminal event, processor manifest, and UI polling timestamp.", ["INC-103"]),
        ("output-collection-failure-runbook.md", "Output Collection Failure Runbook", "Execution completed but output artifacts are missing or duplicated.", "Check OutputCollector idempotency key, StorageAdapter permissions, checksum, and retry history.", ["INC-102", "INC-108"]),
        ("athena-preview-timeout-runbook.md", "Athena Preview Timeout Runbook", "Large output preview query exceeds timeout.", "Confirm partition predicate, row limit, query id, and fallback download message.", ["INC-107"]),
        ("large-file-preview-runbook.md", "Large File Preview Runbook", "Output Preview cannot safely load a large result file.", "Verify size threshold, direct preview disablement, Athena-style query routing, and pagination.", ["INC-104", "INC-107"]),
        ("partial-completion-runbook.md", "Partial Completion Runbook", "Some tasks completed while other tasks failed or were skipped.", "Identify critical vs optional tasks and only mark PARTIAL_SUCCESS when approved output rules are met.", ["INC-105"]),
    ]
    for name, title, scenario, first_check, incidents in runbooks:
        write(
            DOCS / "runbooks" / name,
            section_doc(
                title=title,
                doc_type="runbook",
                component="operations",
                concepts=["operator", "runbook", title.lower()],
                purpose=f"Guides Operators through this synthetic DFP scenario: {scenario}",
                context="Operators connect UI symptoms, backend status, orchestration events, processor output, and storage artifact metadata.",
                behaviors=[
                    first_check,
                    "Capture execution id, job id, workflow version, task id, task type, and last status update.",
                    "Use retry only when status and idempotency rules are clear.",
                ],
                affected=["Execution Monitor", "StatusTracker", "OutputCollector", "AWS-style orchestration", "Operator runbooks"],
                failures=["Stale status", "Retry without idempotency", "Missing partition predicate", "Unsafe user error"],
                tests=["Add regression coverage for linked incident.", "Assert Operator-facing message and audit trail."],
                related_docs=["execution-model.md", "status-tracking-design.md", "output-collection-design.md"],
                code=common_code,
                jira=["DFP-101", "DFP-111", "DFP-112"],
                prs=["PR-505", "PR-510"],
                incidents=incidents,
                notes="OPS should decide whether remediation requires a product change or only runbook clarification.",
            ),
        )

    incidents = [
        ("INC-101-batch-timeout.md", "INC-101", "Batch timeout", "A BATCH_TASK exceeded configured timeout. Execution stayed RUNNING for too long. Operator had to inspect logs and manually mark task failed.", "BatchJobAdapter did not emit a terminal timeout event into StatusTracker.", ["DFP-102", "DFP-111"], ["PR-501"]),
        ("INC-102-duplicate-output.md", "INC-102", "Duplicate output", "OutputCollector retried after a transient storage error but did not use idempotency key. Duplicate result files were produced.", "Collector retry path used artifact key only and did not include execution/task attempt idempotency.", ["DFP-110"], ["PR-503", "PR-508"]),
        ("INC-103-status-stuck-running.md", "INC-103", "Status stuck RUNNING", "Python processor completed successfully, but StatusTracker failed to persist COMPLETED. UI showed RUNNING forever.", "Persistence error was logged but not surfaced as stale status or retryable update.", ["DFP-101", "DFP-109", "DFP-112"], ["PR-502", "PR-505"]),
        ("INC-104-preview-oom.md", "INC-104", "Preview OOM", "Output Preview page attempted to load a full 1.5GB result file instead of paginated preview.", "UI direct preview path did not enforce backend size threshold metadata.", ["DFP-103", "DFP-104"], ["PR-504"]),
        ("INC-105-partial-completion-undefined.md", "INC-105", "Partial completion undefined", "One task failed while other tasks completed. Product behavior for partial result availability was not defined.", "Workflow did not classify optional vs critical tasks and ExecutionStatus lacked PARTIAL_SUCCESS.", ["DFP-106"], ["PR-509"]),
        ("INC-106-invalid-config-upload.md", "INC-106", "Invalid config upload", "User uploaded task-level config with missing required field. Failure was not caught until execution time.", "InputValidator was called during batch execution but not before Execution creation.", ["DFP-107"], ["PR-506"]),
        ("INC-107-athena-preview-timeout.md", "INC-107", "Athena preview timeout", "Large output preview query exceeded timeout due to missing partition predicate.", "AthenaPreviewAdapter accepted preview requests without execution partition filter.", ["DFP-104"], ["PR-504"]),
        ("INC-108-output-permission-denied.md", "INC-108", "Output permission denied", "Operator could see execution succeeded but could not preview output due to storage permission mismatch.", "StorageAdapter used Analyst preview policy but Operator investigation required a separate read path.", ["DFP-110", "DFP-111"], ["PR-508"]),
    ]
    for name, key, title, summary, root_cause, jira, prs in incidents:
        write(
            DOCS / "incidents" / name,
            fm(title, "incident", "incident-history", [key, title.lower(), "operator"], jira=jira, prs=prs, incidents=[key])
            + f"""
            # Incident

            ## Summary
            {key}: {summary}

            ## Timeline
            - 09:05 Analyst reported unexpected ForecastDemo behavior.
            - 09:12 Operator found the affected Execution and TaskExecution.
            - 09:25 TL confirmed cross-layer impact.
            - 09:45 Temporary mitigation was applied in the synthetic demo environment.
            - 10:30 Follow-up Jira and PR review notes were created.

            ## Impact
            Analysts could not confidently determine whether forecast outputs were safe to preview or download. Operators spent extra time correlating Execution status, task logs, and output artifacts.

            ## Root Cause
            {root_cause}

            ## Affected Components
            - Execution Monitor
            - ExecutionService
            - StatusTracker
            - OutputCollector or OutputPreviewService where relevant
            - AWS-style orchestration and Python processor handoff

            ## Detection
            Detected through synthetic Operator investigation using Execution id, task id, lastUpdated timestamp, output artifact metadata, and runbook checks.

            ## Resolution
            Corrected status or output metadata and documented the required product behavior for future implementation.

            ## Follow-up Actions
            - Add regression tests tied to this incident.
            - Update role-specific clarification questions.
            - Ensure future PR reviews check runbook and audit impacts.

            ## Related Docs
            - execution-model.md
            - status-tracking-design.md
            - output-collection-design.md
            - output-preview-design.md

            ## Related Code
            {bullet(common_code)}

            ## Related Jira
            {bullet(jira)}

            ## Related PRs
            {bullet(prs)}

            ## Regression Tests
            Add deterministic tests for the status, retry, output, permission, or preview branch that triggered {key}.
            """,
        )

    jira_items = [
        ("DFP-101-add-execution-status-tracking.md", "DFP-101", "Add execution status tracking", "Analysts need reliable status for long-running forecast Executions.", ["INC-103"], ["PR-502", "PR-505"]),
        ("DFP-102-support-batch-task-retry.md", "DFP-102", "Support retry for failed batch task", "Operators need a safe retry path for failed BATCH_TASK work.", ["INC-101"], ["PR-501"]),
        ("DFP-103-output-preview-pagination.md", "DFP-103", "Add output preview pagination", "Analysts need preview tables that do not load full result files.", ["INC-104"], ["PR-504"]),
        ("DFP-104-athena-large-file-preview.md", "DFP-104", "Use Athena-style query for large file preview", "Large outputs need query-based preview with partition predicates.", ["INC-107", "INC-104"], ["PR-504"]),
        ("DFP-105-workflow-versioning.md", "DFP-105", "Add workflow versioning", "Admins need immutable workflow versions for reproducible Executions.", ["INC-105"], ["PR-507"]),
        ("DFP-106-partial-execution-recovery.md", "DFP-106", "Define partial execution recovery", "BA and TL need clear behavior when optional tasks fail.", ["INC-105"], ["PR-509"]),
        ("DFP-107-task-level-config-validation.md", "DFP-107", "Validate task-level config before execution", "Invalid config should fail before expensive execution starts.", ["INC-106"], ["PR-506"]),
        ("DFP-108-admin-workflow-console.md", "DFP-108", "Create admin workflow console", "Admins need UI to manage workflow and task definitions.", [], ["PR-507"]),
        ("DFP-109-execution-monitor-auto-refresh.md", "DFP-109", "Add execution monitor auto-refresh", "Analysts need status updates without manual refresh.", ["INC-103"], ["PR-502"]),
        ("DFP-110-output-collection-idempotency.md", "DFP-110", "Make output collection idempotent", "OutputCollector retry must not duplicate result files.", ["INC-102", "INC-108"], ["PR-503", "PR-508"]),
        ("DFP-111-operator-retry-action.md", "DFP-111", "Add operator retry action", "Operators need controlled retry for eligible failed tasks.", ["INC-101", "INC-108"], ["PR-501"]),
        ("DFP-112-job-execution-audit-log.md", "DFP-112", "Add job execution audit log", "Status changes and operator actions need audit history.", ["INC-103"], ["PR-510"]),
    ]
    for name, key, title, background, incident_refs, pr_refs in jira_items:
        write(
            DOCS / "historical-jira" / name,
            fm(title, "historical-jira", "delivery-history", [key, title.lower()], jira=[key], prs=pr_refs, incidents=incident_refs)
            + f"""
            # Jira Story

            ## Key
            {key}

            ## Title
            {title}

            ## Background
            {background} This synthetic Jira story lets DREAM retrieve historical delivery patterns for DFP requirement analysis.

            ## User Story
            As a DFP stakeholder, I want {title.lower()} so that Analysts, Operators, and Admins can handle forecast Executions with less ambiguity.

            ## Functional Requirements
            - Preserve Job, Workflow, Task, and Execution vocabulary.
            - Update affected UI, backend, orchestration, processor, or runbook components as needed.
            - Surface user-safe messages for Analyst and Operator workflows.
            - Record audit-friendly status, retry, output, or configuration decisions.

            ## Acceptance Criteria
            - Relevant happy path and failure path are covered.
            - Impact on Execution status, Task status, output artifacts, or Workflow versioning is documented.
            - Role-specific open questions are resolved before implementation.
            - Regression tests link back to related incidents when present.

            ## Affected Components
            - Execution Monitor or Output Preview Page when UI behavior changes.
            - Java controllers, services, domain models, adapters, and collectors.
            - AWS-style state machine or processor boundary when orchestration changes.
            - Runbooks and PR review checklists.

            ## Dev Notes
            Use synthetic DFP code paths and do not introduce real external endpoints.

            ## Test Scenarios
            - Success path for requested behavior.
            - Failure or timeout path.
            - Operator investigation or retry path when applicable.
            - Regression path for linked incidents.

            ## Open Questions
            - Which role owns final behavior wording?
            - Which statuses should be visible in the UI?
            - Does this require runbook or audit log updates?

            ## Related Incidents
            {bullet(incident_refs)}

            ## Related PRs
            {bullet(pr_refs)}

            ## Current Status
            Synthetic completed story used for DREAM demo retrieval.
            """,
        )

    pr_items = [
        ("PR-501-add-batch-job-adapter.md", "PR-501", "Add BatchJobAdapter", ["backend-api/src/main/java/com/democorp/dfp/adapters/BatchJobAdapter.java"], ["DFP-102", "DFP-111"], ["INC-101"]),
        ("PR-502-add-execution-status-polling.md", "PR-502", "Add execution status polling", ["frontend/src/app/execution/execution-monitor.component.ts", "frontend/src/app/services/job-api.service.ts"], ["DFP-101", "DFP-109"], ["INC-103"]),
        ("PR-503-output-collector-retry-logic.md", "PR-503", "OutputCollector retry logic", ["backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java"], ["DFP-110"], ["INC-102"]),
        ("PR-504-athena-preview-optimization.md", "PR-504", "Athena preview optimization", ["backend-api/src/main/java/com/democorp/dfp/adapters/AthenaPreviewAdapter.java"], ["DFP-103", "DFP-104"], ["INC-104", "INC-107"]),
        ("PR-505-status-tracker-persistence.md", "PR-505", "StatusTracker persistence", ["backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java"], ["DFP-101"], ["INC-103"]),
        ("PR-506-task-config-validation.md", "PR-506", "Task config validation", ["backend-api/src/main/java/com/democorp/dfp/workflow/TaskDefinition.java", "python-processors/processors/input_validator.py"], ["DFP-107"], ["INC-106"]),
        ("PR-507-admin-workflow-console.md", "PR-507", "Admin workflow console", ["frontend/src/app/jobs/job-detail.component.ts", "backend-api/src/main/java/com/democorp/dfp/workflow/WorkflowController.java"], ["DFP-105", "DFP-108"], []),
        ("PR-508-output-collection-idempotency.md", "PR-508", "Output collection idempotency", ["backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java", "backend-api/src/main/java/com/democorp/dfp/output/OutputArtifact.java"], ["DFP-110"], ["INC-102", "INC-108"]),
        ("PR-509-partial-success-status.md", "PR-509", "Partial success status", ["backend-api/src/main/java/com/democorp/dfp/execution/ExecutionStatus.java", "backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java"], ["DFP-106"], ["INC-105"]),
        ("PR-510-execution-audit-log.md", "PR-510", "Execution audit log", ["backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java"], ["DFP-112"], ["INC-103"]),
    ]
    comments = [
        "Please confirm BATCH_TASK timeout behavior is visible to Operator.",
        "This PR updates backend status but does not update Execution Monitor error state.",
        "Missing regression test for duplicate output retry.",
        "Need to update runbook for stuck RUNNING state.",
    ]
    for name, pr_id, title, files, jira_refs, incident_refs in pr_items:
        write(
            DOCS / "historical-pr" / name,
            fm(title, "historical-pr", "delivery-history", [pr_id, title.lower()], code=files, jira=jira_refs, prs=[pr_id], incidents=incident_refs)
            + f"""
            # Pull Request

            ## PR ID
            {pr_id}

            ## Title
            {title}

            ## Summary
            Synthetic DFP pull request documenting a historical implementation pattern. DREAM uses this to reason about PR review risks and likely missing tests.

            ## Files Changed
            {bullet(files)}

            ## Important Design Decisions
            - Kept changes scoped to DFP demo components.
            - Preserved Job, Workflow, Task, and Execution vocabulary.
            - Used deterministic behavior and human-reviewable status/output decisions.
            - Avoided real external integrations.

            ## Reviewer Comments
            {bullet(comments)}

            ## Test Coverage
            Unit tests were expected for status transitions, output idempotency, preview pagination, retry decisions, or config validation depending on scope.

            ## Risks
            - Cross-layer UI/backend drift.
            - Missing Operator runbook update.
            - Ambiguous status or partial output behavior.
            - Insufficient regression coverage for linked incidents.

            ## Follow-up Items
            - Update related docs and runbooks.
            - Add explicit regression tests.
            - Confirm role-specific open questions are resolved.

            ## Related Jira
            {bullet(jira_refs)}

            ## Related Incidents
            {bullet(incident_refs)}

            ## Related Runbooks
            - status-stuck-running-runbook.md
            - output-collection-failure-runbook.md
            - partial-completion-runbook.md
            """,
        )

    for folder, items in {
        "testing": [
            "unit-test-guidelines.md",
            "status-transition-test-plan.md",
            "output-preview-test-plan.md",
            "batch-task-retry-test-plan.md",
            "partial-completion-test-plan.md",
            "regression-test-matrix.md",
        ],
        "pr-review": [
            "review-checklist.md",
            "async-execution-review-checklist.md",
            "output-collection-review-checklist.md",
            "frontend-status-review-checklist.md",
        ],
    }.items():
        for item in items:
            title = item.removesuffix(".md").replace("-", " ").title()
            write(
                DOCS / folder / item,
                section_doc(
                    title=title,
                    doc_type=folder,
                    component="quality" if folder == "testing" else "review",
                    concepts=[title.lower(), "regression", "review"],
                    purpose=f"Provides DFP {folder} guidance for {title.lower()}.",
                    context="DREAM should connect tests and PR review to docs, code, incidents, Jira history, and runbooks.",
                    behaviors=[
                        "Check status transitions and task-level behavior.",
                        "Check SERVICE_TASK versus BATCH_TASK differences.",
                        "Check output idempotency, preview limits, partial completion, and audit logging.",
                    ],
                    affected=["ExecutionServiceTest", "StatusTrackerTest", "OutputCollectorTest", "Execution Monitor"],
                    failures=["Missing transition tests", "Duplicate output retry gap", "No stale RUNNING check", "No invalid config preflight test"],
                    tests=["Use deterministic synthetic data.", "Mock adapters.", "Add one regression for each linked incident."],
                    related_docs=["execution-model.md", "status-tracking-design.md", "output-collection-design.md"],
                    code=common_code,
                    jira=["DFP-101", "DFP-106", "DFP-110"],
                    prs=["PR-505", "PR-508", "PR-509"],
                    incidents=["INC-102", "INC-103", "INC-105"],
                    notes="If a change touches status, output, preview, retry, or config validation, check docs, runbooks, and audit behavior.",
                ),
            )

    concept_items = [
        ("execution-status-memory.md", "Execution Status", "Execution, TaskExecution", "Execution Monitor", "StatusTracker, ExecutionService, ExecutionController", "Step Functions events and stale status metrics", "ForecastProcessor completion callback", "StatusTrackerTest and status-transition-test-plan.md", ["INC-103", "INC-105"], ["DFP-101", "DFP-109", "DFP-112"], ["PR-502", "PR-505", "PR-510"], "Always ask which statuses are user-visible, stale, retryable, and terminal."),
        ("batch-task-memory.md", "Batch Task", "Task, Workflow, Execution", "Execution Monitor task timeline", "BatchJobAdapter, ExecutionService", "Batch runner, retry, timeout, metrics", "ForecastProcessor and DataTransformer", "batch-task-retry-test-plan.md", ["INC-101"], ["DFP-102", "DFP-111"], ["PR-501"], "Always separate BATCH_TASK timeout/retry behavior from SERVICE_TASK behavior."),
        ("output-preview-memory.md", "Output Preview", "OutputArtifact, Execution", "Output Preview Page", "OutputPreviewService, AthenaPreviewAdapter", "Athena-like query and S3-like storage", "OutputAggregator manifest metadata", "output-preview-test-plan.md", ["INC-104", "INC-107", "INC-108"], ["DFP-103", "DFP-104"], ["PR-504"], "Always ask size threshold, pagination, partition predicate, and permission behavior."),
        ("output-collection-memory.md", "Output Collection", "OutputArtifact, TaskExecution", "Output availability and download actions", "OutputCollector, StorageAdapter", "S3-like object storage retry", "OutputAggregator", "OutputCollectorTest", ["INC-102", "INC-108"], ["DFP-110"], ["PR-503", "PR-508"], "Always check idempotency key, retry, checksum, and duplicate artifact handling."),
        ("partial-recovery-memory.md", "Partial Recovery", "Execution, Workflow, Task", "PARTIAL_SUCCESS banner and partial output display", "ExecutionService, StatusTracker", "Optional task failure branch", "OutputAggregator partial manifest", "partial-completion-test-plan.md", ["INC-105"], ["DFP-106"], ["PR-509"], "Always ask which tasks are critical and whether partial outputs may be previewed or downloaded."),
        ("config-validation-memory.md", "Config Validation", "TaskDefinition, Job", "Task-level upload validation messages", "JobController, WorkflowService", "Service task preflight validation", "InputValidator", "test_input_validator.py", ["INC-106"], ["DFP-107"], ["PR-506"], "Always ask whether invalid config blocks Execution creation or fails a Task after start."),
    ]
    for name, title, domain_objects, ui, java, cloud, py, tests, incident_refs, jira_refs, pr_refs, hint in concept_items:
        write(
            DOCS / "concepts" / name,
            fm(f"Concept Memory: {title}", "concept", title.lower().replace(" ", "-"), [title.lower(), "concept memory"], jira=jira_refs, prs=pr_refs, incidents=incident_refs)
            + f"""
            # Concept Memory: {title}

            ## What It Means
            {title} is a high-value DFP concept used to connect rough requirements, codebase evidence, incidents, Jira history, PR history, tests, and runbooks.

            ## Related Domain Objects
            {domain_objects}

            ## Related UI Areas
            {ui}

            ## Related Java Backend Classes
            {java}

            ## Related AWS / Cloud Components
            {cloud}

            ## Related Python Processors
            {py}

            ## Related Tests
            {tests}

            ## Related Incidents
            {bullet(incident_refs)}

            ## Related Jira
            {bullet(jira_refs)}

            ## Related PRs
            {bullet(pr_refs)}

            ## Common Risks
            - Requirement only mentions one layer while behavior crosses UI, backend, orchestration, processors, and operations.
            - Missing regression test for a known incident.
            - User-facing message does not match backend status semantics.
            - Runbook or audit behavior is not updated.

            ## Common Review Questions
            - Which role owns the expected behavior?
            - What is the terminal state and how is it displayed?
            - What evidence proves the output or status is safe?
            - Which tests prove the failure mode will not repeat?

            ## Requirement Analysis Hints
            {hint} Link the request to related incidents and historical PRs before drafting scope.

            ## PR Review Hints
            Check changed files against related tests, runbooks, and previous reviewer comments. Flag missing status, retry, idempotency, preview, or validation tests.
            """,
        )


def build_codebase() -> None:
    write(
        DFP / "README.md",
        """
        # DemoCorp Forecast Platform Demo Repo

        Synthetic multi-layer repository for DREAM demos. It is not connected to any real company, cloud account, repository, ticket, or internal system.

        Layers:
        - Angular-like frontend for Jobs, Execution Monitor, Output Preview, and Admin workflows.
        - Spring Boot-like Java backend for Jobs, Workflows, Executions, Outputs, and adapters.
        - AWS-style orchestration artifacts.
        - Python processors for validation, forecast processing, transformation, and aggregation.
        """,
    )
    ts_files = {
        "frontend/src/app/jobs/job-list.component.ts": "export class JobListComponent { columns = ['name', 'owner', 'workflow', 'status']; statusLabel(status: string): string { return status.toLowerCase().replace('_', ' '); } }",
        "frontend/src/app/jobs/job-detail.component.ts": "export class JobDetailComponent { selectedWorkflowVersion = 'baseline-v3'; validateTaskUpload(taskId: string, fileName: string): string { return taskId && fileName ? 'valid' : 'missing task upload'; } executeJob(): string { return 'Execution queued'; } }",
        "frontend/src/app/execution/execution-status.model.ts": "export type ExecutionStatus = 'QUEUED' | 'RUNNING' | 'FAILED' | 'COMPLETED' | 'CANCELLED' | 'PARTIAL_SUCCESS'; export type TaskStatus = 'PENDING' | 'QUEUED' | 'RUNNING' | 'FAILED' | 'COMPLETED' | 'SKIPPED' | 'RETRYING'; export interface ExecutionStatusView { executionId: string; status: ExecutionStatus; activeTaskId?: string; staleRunning: boolean; }",
        "frontend/src/app/execution/execution-monitor.component.ts": "import { Subscription, interval, switchMap } from 'rxjs'; import { JobApiService } from '../services/job-api.service'; export class ExecutionMonitorComponent { execution?: unknown; private refreshSubscription?: Subscription; constructor(private readonly jobApi: JobApiService) {} startAutoRefresh(executionId: string): void { this.refreshSubscription = interval(15000).pipe(switchMap(() => this.jobApi.getExecutionStatus(executionId))).subscribe(status => { this.execution = status; }); } stopAutoRefresh(): void { this.refreshSubscription?.unsubscribe(); } }",
        "frontend/src/app/output/output-preview.component.ts": "import { JobApiService } from '../services/job-api.service'; export class OutputPreviewComponent { page = 1; timeoutMessage?: string; constructor(private readonly jobApi: JobApiService) {} loadPreview(executionId: string, artifactId: string): void { this.jobApi.requestOutputPreview(executionId, artifactId, this.page).subscribe({ error: () => { this.timeoutMessage = 'Preview timed out. Try a narrower partition.'; } }); } }",
        "frontend/src/app/services/job-api.service.ts": "import { Observable, of } from 'rxjs'; export class JobApiService { getExecutionStatus(executionId: string): Observable<unknown> { return of({ executionId, status: 'RUNNING', staleRunning: false }); } requestOutputPreview(executionId: string, artifactId: string, page: number): Observable<unknown> { return of({ executionId, artifactId, page, rows: [] }); } }",
    }
    for path, body in ts_files.items():
        write(DFP / path, body)

    java = {
        "job/Job.java": "public class Job { public String id; public String name; public String owner; public String workflowId; public String workflowVersion; public String status; public String createdAt; public String updatedAt; }",
        "job/JobService.java": "public class JobService { public Job createJob(String name, String owner, String workflowId, String workflowVersion) { Job job = new Job(); job.id = \"job-demo-\" + Math.abs(name.hashCode()); job.name = name; job.owner = owner; job.workflowId = workflowId; job.workflowVersion = workflowVersion; job.status = \"DRAFT\"; return job; } public boolean canExecute(Job job) { return job != null && !\"RUNNING\".equals(job.status); } }",
        "job/JobController.java": "public class JobController { private final JobService jobService = new JobService(); public Job createJob(String name, String owner, String workflowId, String workflowVersion) { return jobService.createJob(name, owner, workflowId, workflowVersion); } public String validateTaskConfigBeforeExecution(String taskId, String configJson) { if (configJson == null || !configJson.contains(\"forecastHorizon\")) { return \"Missing required task config field forecastHorizon\"; } return \"valid\"; } }",
        "workflow/WorkflowController.java": "public class WorkflowController { private final WorkflowService workflowService = new WorkflowService(); public WorkflowDefinition publish(WorkflowDefinition draft) { return workflowService.publishDraft(draft); } }",
        "workflow/WorkflowService.java": "public class WorkflowService { public WorkflowDefinition publishDraft(WorkflowDefinition draft) { draft.published = true; return draft; } public boolean canEditInPlace(WorkflowDefinition workflowDefinition) { return workflowDefinition != null && !workflowDefinition.published; } }",
        "workflow/WorkflowDefinition.java": "import java.util.List; public class WorkflowDefinition { public String workflowId; public String version; public boolean published; public List<TaskDefinition> tasks; public boolean isImmutableForJobs() { return published; } }",
        "workflow/TaskDefinition.java": "import java.util.List; public class TaskDefinition { public String taskId; public String displayName; public TaskType taskType; public List<String> dependencies; public int timeoutSeconds; public int maxRetryAttempts; public List<String> requiredConfigFields; public boolean requiresConfigField(String fieldName) { return requiredConfigFields != null && requiredConfigFields.contains(fieldName); } }",
        "workflow/TaskType.java": "public enum TaskType { SERVICE_TASK, BATCH_TASK }",
        "execution/ExecutionController.java": "public class ExecutionController { private final ExecutionService executionService = new ExecutionService(); public Execution startExecution(String jobId) { return executionService.startExecution(jobId, TaskType.BATCH_TASK); } public String status(String executionId) { return \"status:\" + executionId; } }",
        "execution/ExecutionService.java": "public class ExecutionService { private final StatusTracker statusTracker = new StatusTracker(); private final BatchJobAdapter batchJobAdapter = new BatchJobAdapter(); private final OutputCollector outputCollector = new OutputCollector(); public Execution startExecution(String jobId, TaskType firstTaskType) { Execution execution = new Execution(); execution.executionId = \"exec-\" + jobId; execution.jobId = jobId; statusTracker.markExecutionQueued(execution.executionId); statusTracker.markExecutionRunning(execution.executionId); if (firstTaskType == TaskType.BATCH_TASK) { batchJobAdapter.submitBatchTask(execution.executionId, \"task-forecast-batch\"); } return execution; } public ExecutionStatus resolveFinalStatus(boolean criticalTaskFailed, boolean optionalTaskFailed) { if (criticalTaskFailed) { return ExecutionStatus.FAILED; } if (optionalTaskFailed) { return ExecutionStatus.PARTIAL_SUCCESS; } return ExecutionStatus.COMPLETED; } public void collectOutputsAfterCompletion(String executionId) { outputCollector.collectForExecution(executionId, \"task-forecast-batch\", \"attempt-1\"); } }",
        "execution/Execution.java": "import java.util.ArrayList; import java.util.List; public class Execution { public String executionId; public String jobId; public ExecutionStatus status = ExecutionStatus.QUEUED; public String startTime; public String endTime; public List<TaskExecution> taskExecutions = new ArrayList<>(); }",
        "execution/ExecutionStatus.java": "public enum ExecutionStatus { QUEUED, RUNNING, FAILED, COMPLETED, CANCELLED, PARTIAL_SUCCESS }",
        "execution/TaskExecution.java": "public class TaskExecution { public String taskId; public String taskName; public String taskType; public TaskStatus status; public int attemptCount; public String lastUpdated; public boolean critical; }",
        "execution/TaskStatus.java": "public enum TaskStatus { PENDING, QUEUED, RUNNING, FAILED, COMPLETED, SKIPPED, RETRYING }",
        "execution/StatusTracker.java": "import java.time.Instant; import java.util.HashMap; import java.util.Map; public class StatusTracker { private final Map<String, ExecutionStatus> executionStatuses = new HashMap<>(); private final Map<String, Instant> lastUpdated = new HashMap<>(); public void markExecutionQueued(String executionId) { persistStatus(executionId, ExecutionStatus.QUEUED); } public void markExecutionRunning(String executionId) { persistStatus(executionId, ExecutionStatus.RUNNING); } public void markExecutionCompleted(String executionId) { persistStatus(executionId, ExecutionStatus.COMPLETED); } public void markExecutionFailed(String executionId) { persistStatus(executionId, ExecutionStatus.FAILED); } public void markPartialSuccess(String executionId) { persistStatus(executionId, ExecutionStatus.PARTIAL_SUCCESS); } public boolean isStaleRunning(String executionId, Instant now) { return executionStatuses.get(executionId) == ExecutionStatus.RUNNING && lastUpdated.containsKey(executionId) && lastUpdated.get(executionId).plusSeconds(900).isBefore(now); } private void persistStatus(String executionId, ExecutionStatus status) { executionStatuses.put(executionId, status); lastUpdated.put(executionId, Instant.now()); } }",
        "output/OutputCollector.java": "import java.util.HashSet; import java.util.Set; public class OutputCollector { private final Set<String> collectedIdempotencyKeys = new HashSet<>(); public OutputArtifact collectForExecution(String executionId, String taskId, String attemptId) { String idempotencyKey = executionId + \":\" + taskId + \":\" + attemptId; if (collectedIdempotencyKeys.contains(idempotencyKey)) { return existingArtifact(executionId, taskId, idempotencyKey); } collectedIdempotencyKeys.add(idempotencyKey); OutputArtifact artifact = new OutputArtifact(); artifact.executionId = executionId; artifact.taskId = taskId; artifact.storageKey = \"dfp-demo/\" + executionId + \"/\" + taskId + \"/result.csv\"; artifact.idempotencyKey = idempotencyKey; artifact.checksum = \"synthetic-checksum\"; return artifact; } private OutputArtifact existingArtifact(String executionId, String taskId, String idempotencyKey) { OutputArtifact artifact = new OutputArtifact(); artifact.executionId = executionId; artifact.taskId = taskId; artifact.idempotencyKey = idempotencyKey; artifact.storageKey = \"existing-artifact\"; return artifact; } }",
        "output/OutputArtifact.java": "public class OutputArtifact { public String executionId; public String taskId; public String storageKey; public String checksum; public long sizeBytes; public String idempotencyKey; public boolean partial; }",
        "output/OutputPreviewService.java": "public class OutputPreviewService { private final StorageAdapter storageAdapter = new StorageAdapter(); private final AthenaPreviewAdapter athenaPreviewAdapter = new AthenaPreviewAdapter(); public String preview(OutputArtifact artifact, int page) { if (artifact.sizeBytes > 100000000L) { return athenaPreviewAdapter.previewPartition(artifact.executionId, artifact.taskId, page); } return storageAdapter.previewSmallObject(artifact.storageKey, page); } }",
        "adapters/BatchJobAdapter.java": "public class BatchJobAdapter { public String submitBatchTask(String executionId, String taskId) { return \"batch-\" + executionId + \"-\" + taskId; } public boolean isRetryAllowed(String taskId, int attemptCount) { return taskId != null && attemptCount < 3; } }",
        "adapters/ServiceTaskAdapter.java": "public class ServiceTaskAdapter { public String invokeServiceTask(String executionId, String taskId) { return \"service-task-completed:\" + executionId + \":\" + taskId; } }",
        "adapters/StorageAdapter.java": "public class StorageAdapter { public String previewSmallObject(String storageKey, int page) { if (storageKey == null) { return \"permission-denied\"; } return \"preview-page-\" + page; } }",
        "adapters/AthenaPreviewAdapter.java": "public class AthenaPreviewAdapter { public String previewPartition(String executionId, String taskId, int page) { if (executionId == null || taskId == null) { return \"missing-partition-predicate\"; } return \"athena-preview:\" + executionId + \":\" + taskId + \":page:\" + page; } }",
    }
    for rel, body in java.items():
        package = "com.democorp.dfp." + rel.split("/")[0]
        write(
            DFP / "backend-api/src/main/java/com/democorp/dfp" / rel,
            f"package {package};\n\n/** Synthetic DFP code for DREAM codebase memory demos. */\n{body}\n",
        )
    java_tests = {
        "execution/ExecutionServiceTest.java": "class ExecutionServiceTest { @Test void resolvesPartialSuccessWhenOnlyOptionalTaskFails() { assertEquals(ExecutionStatus.PARTIAL_SUCCESS, new ExecutionService().resolveFinalStatus(false, true)); } }",
        "execution/StatusTrackerTest.java": "class StatusTrackerTest { @Test void queuedExecutionIsNotStaleRunning() { StatusTracker tracker = new StatusTracker(); tracker.markExecutionQueued(\"exec-1\"); assertFalse(tracker.isStaleRunning(\"exec-1\", Instant.now())); } }",
        "output/OutputCollectorTest.java": "class OutputCollectorTest { @Test void retryUsesSameIdempotencyKey() { OutputArtifact artifact = new OutputCollector().collectForExecution(\"exec-1\", \"task-1\", \"attempt-1\"); assertEquals(\"exec-1:task-1:attempt-1\", artifact.idempotencyKey); } }",
        "output/OutputPreviewServiceTest.java": "class OutputPreviewServiceTest { @Test void largeArtifactUsesPartitionPreview() { OutputArtifact artifact = new OutputArtifact(); artifact.executionId = \"exec-1\"; artifact.taskId = \"task-1\"; artifact.sizeBytes = 1500000000L; assertEquals(\"athena-preview:exec-1:task-1:page:1\", new OutputPreviewService().preview(artifact, 1)); } }",
    }
    for rel, body in java_tests.items():
        package = "com.democorp.dfp." + rel.split("/")[0]
        write(
            DFP / "backend-api/src/test/java/com/democorp/dfp" / rel,
            f"package {package};\n\n/** Synthetic test file for DREAM codebase memory. */\n{body}\n",
        )

    py_files = {
        "python-processors/processors/input_validator.py": """
            from __future__ import annotations


            class InputValidator:
                required_fields = {"forecastHorizon", "sourceDataset", "owner"}

                def validate_task_config(self, config: dict[str, object]) -> list[str]:
                    missing = sorted(field for field in self.required_fields if field not in config)
                    errors = [f"missing required field: {field}" for field in missing]
                    horizon = config.get("forecastHorizon")
                    if horizon is not None and (not isinstance(horizon, int) or horizon <= 0):
                        errors.append("forecastHorizon must be a positive integer")
                    return errors
        """,
        "python-processors/processors/forecast_processor.py": """
            from __future__ import annotations


            class ForecastProcessor:
                def run_forecast(
                    self,
                    execution_id: str,
                    task_id: str,
                    rows: list[dict[str, object]],
                ) -> dict[str, object]:
                    return {
                        "executionId": execution_id,
                        "taskId": task_id,
                        "rowCount": len(rows),
                        "status": "COMPLETED",
                    }
        """,
        "python-processors/processors/data_transformer.py": """
            from __future__ import annotations


            class DataTransformer:
                def normalize_rows(
                    self, rows: list[dict[str, object]]
                ) -> list[dict[str, object]]:
                    return [{str(key).lower(): value for key, value in row.items()} for row in rows]
        """,
        "python-processors/processors/output_aggregator.py": """
            from __future__ import annotations

            import hashlib


            class OutputAggregator:
                def build_manifest(
                    self, execution_id: str, task_id: str, attempt_id: str, row_count: int
                ) -> dict[str, object]:
                    idempotency_key = f"{execution_id}:{task_id}:{attempt_id}"
                    checksum = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:12]
                    return {
                        "executionId": execution_id,
                        "taskId": task_id,
                        "attemptId": attempt_id,
                        "idempotencyKey": idempotency_key,
                        "checksum": checksum,
                        "rowCount": row_count,
                        "storageKey": f"dfp-demo/{execution_id}/{task_id}/result.csv",
                    }
        """,
        "python-processors/tests/test_input_validator.py": """
            import sys
            from pathlib import Path

            PROCESSOR_ROOT = Path(__file__).resolve().parents[1]
            sys.path.insert(0, str(PROCESSOR_ROOT))

            from processors.input_validator import InputValidator  # noqa: E402


            def test_validator_reports_missing_forecast_horizon() -> None:
                errors = InputValidator().validate_task_config(
                    {"sourceDataset": "demo", "owner": "analyst"}
                )
                assert "missing required field: forecastHorizon" in errors
        """,
        "python-processors/tests/test_output_aggregator.py": """
            import sys
            from pathlib import Path

            PROCESSOR_ROOT = Path(__file__).resolve().parents[1]
            sys.path.insert(0, str(PROCESSOR_ROOT))

            from processors.output_aggregator import OutputAggregator  # noqa: E402


            def test_manifest_contains_stable_idempotency_key() -> None:
                manifest = OutputAggregator().build_manifest("exec-1", "task-1", "attempt-1", 10)
                assert manifest["idempotencyKey"] == "exec-1:task-1:attempt-1"
                assert manifest["storageKey"] == "dfp-demo/exec-1/task-1/result.csv"
        """,
    }
    for path, body in py_files.items():
        write(DFP / path, body)

    write(DFP / "aws/README.md", "# DFP AWS-Style Orchestration Notes\n\nSynthetic orchestration files only.")
    write(
        DFP / "aws/step-functions/job-execution-state-machine.asl.json",
        """
        {
          "Comment": "Synthetic DFP job execution state machine for DREAM demos.",
          "StartAt": "ValidateInput",
          "States": {
            "ValidateInput": { "Type": "Task", "Resource": "lambda:service_task_handler", "Next": "RunForecastBatch" },
            "RunForecastBatch": { "Type": "Task", "Resource": "batch:batch_task_entrypoint", "Next": "CollectOutputs", "TimeoutSeconds": 3600 },
            "CollectOutputs": { "Type": "Task", "Resource": "lambda:service_task_handler", "End": true }
          }
        }
        """,
    )
    write(
        DFP / "aws/lambda/service_task_handler.py",
        """
        from __future__ import annotations


        def handle_service_task(
            event: dict[str, object], context: object | None = None
        ) -> dict[str, object]:
            execution_id = str(event.get("executionId", "missing-execution"))
            task_id = str(event.get("taskId", "service-task"))
            return {
                "executionId": execution_id,
                "taskId": task_id,
                "status": "COMPLETED",
                "context": str(context),
            }
        """,
    )
    write(
        DFP / "aws/batch/batch_task_entrypoint.py",
        """
        from __future__ import annotations


        def run_batch_task(execution_id: str, task_id: str, attempt_count: int) -> dict[str, object]:
            if attempt_count > 3:
                return {"executionId": execution_id, "taskId": task_id, "status": "FAILED"}
            return {"executionId": execution_id, "taskId": task_id, "status": "COMPLETED"}
        """,
    )
    write(
        DFP / "docs/local-architecture-note.md",
        "# Local Architecture Note\n\nSynthetic DFP demo repository used by DREAM codebase memory.",
    )


def build_examples_and_docs() -> None:
    diffs = {
        "DFP-109-execution-monitor-auto-refresh.diff": "frontend/src/app/execution/execution-monitor.component.ts",
        "DFP-110-output-collector-idempotency.diff": "backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java",
        "DFP-106-partial-execution-recovery.diff": "backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java",
        "DFP-107-task-config-validation.diff": "backend-api/src/main/java/com/democorp/dfp/job/JobController.java",
    }
    for filename, path in diffs.items():
        write(
            EXAMPLES / "pr-diffs" / filename,
            f"""
            diff --git a/{path} b/{path}
            --- a/{path}
            +++ b/{path}
            @@ -1,4 +1,12 @@
            +// Synthetic DFP change for {filename}
            +// Adds behavior connected to status, output, partial recovery, or config validation.
            +public String demoChange(String executionId) {{
            +    return "changed:" + executionId;
            +}}
            diff --git a/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java b/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java
            --- a/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java
            +++ b/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java
            @@ -1,4 +1,9 @@
            +@Test
            +void syntheticRegressionForDfpChange() {{
            +    assertTrue(true);
            +}}
            """,
        )
    requests = {
        "async-status-tracking.md": "Users want to know which task is still running when a forecast job takes too long. The execution page should show better progress.",
        "partial-execution-recovery.md": "If one optional task fails but the main forecast output is usable, the system should let users see partial results somehow.",
        "large-output-preview.md": "Large forecast outputs should be previewable without downloading the whole file.",
        "task-config-validation.md": "Bad task config should be caught earlier before long-running execution starts.",
        "operator-retry-action.md": "Operators need a safe way to retry failed forecast tasks from the monitor.",
        "workflow-versioning.md": "Admins need to update workflow tasks without changing past jobs.",
    }
    for filename, request in requests.items():
        write(
            EXAMPLES / "requirement-requests" / filename,
            f"""
            # Rough Request

            ## Written By
            BA

            ## Request
            {request}

            ## Notes
            This request is intentionally incomplete and written in business language.

            ## Ambiguities
            - Status labels, runbook impact, test scope, and ownership are unclear.
            - UI, Java backend, AWS orchestration, and Python processor impact may differ.

            ## Expected DREAM Output
            DREAM should retrieve DFP concept memory, fake incidents, Jira history, PR history, and codebase evidence before generating questions, impact map, engineering brief, and Jira draft.
            """,
        )
    outputs = {
        "engineering-brief-async-status-example.md": "# Engineering Brief\n\n## 1. Request Summary\nUsers want to know which task is still running when a forecast job takes too long.\n\n## 4. Impact Map\n- frontend: Execution Monitor polling and stale warning.\n- backend: StatusTracker, ExecutionService, ExecutionController.\n- ops: status-stuck-running runbook.\n\n## 11. Sources Used\n- status-tracking-design.md\n- INC-103-status-stuck-running.md\n- StatusTracker.java",
        "jira-draft-async-status-example.md": "# Jira Story Draft\n\n## Title\nAdd Execution Monitor task-level status progress\n\n## Acceptance Criteria\n- Active task is visible.\n- Stale RUNNING warning appears.\n- Status transition tests cover terminal states.\n\n## Open Questions\n- What stale threshold should OPS own?",
        "pr-review-output-collector-example.md": "# AI PR Review Summary\n\n## Overall Risk\nMedium\n\n## Related Codebase Memory\nOutputCollector relates to DFP-110, INC-102, PR-508, and output-collection-memory.md.\n\n## Test Coverage Comments\nAdd duplicate output retry regression.",
        "impact-map-partial-recovery-example.md": "# Impact Map: Partial Execution Recovery\n\n- workflow: optional vs critical task semantics.\n- backend: ExecutionStatus.PARTIAL_SUCCESS.\n- frontend: partial output display.\n- test: missing critical-task failure regression.",
        "role-questions-async-status-example.md": "# Role Questions: Async Status\n\n## BA\n- Which status labels should Analysts see?\n\n## TL\n- Is stale RUNNING backend-owned or UI-derived?\n\n## FE\n- What polling interval should be used?\n\n## BE\n- Which event writes each transition?\n\n## QA\n- Which transition matrix is required?\n\n## OPS\n- What stale threshold triggers runbook action?",
    }
    for filename, content in outputs.items():
        write(EXAMPLES / "outputs" / filename, content)
    write(
        ROOT / "docs" / "demo-dataset.md",
        """
        <!-- SPDX-License-Identifier: Apache-2.0 -->

        # Demo Dataset: DemoCorp Forecast Platform

        DFP is a synthetic enterprise forecast and analytics product used to demonstrate DREAM as a codebase-aware engineering memory platform.

        ## Core Objects
        Job, Workflow, Task, Execution, and OutputArtifact.

        ## Architecture Layers
        UI, Java backend, AWS-style orchestration, and Python processors.

        ## User Roles
        Analyst, Operator, Admin, BA, TL, FE, BE, QA, and OPS.

        ## Folder Structure
        The dataset includes domain docs, architecture docs, runbooks, incidents, historical Jira, historical PRs, testing docs, PR review docs, concept memory, fake code, fake diffs, rough requests, and example outputs.

        ## Requirement Intelligence
        Use `examples/requirement-requests` to create Requirement Cases and retrieve evidence from docs and codebase memory.

        ## PR Review
        Use `examples/pr-diffs` with historical Jira docs to review DFP changes with codebase memory.

        ## Codebase Memory
        Index `examples/dfp-demo-repo` and search for `status tracker`, `duplicate output`, `partial success`, `Athena preview`, or `task config validation`.
        """,
    )
    write(
        ROOT / "docs" / "mock-world-model.md",
        """
        <!-- SPDX-License-Identifier: Apache-2.0 -->

        # Mock World Model

        ## Job
        A user-created forecast case with name, owner, workflow, status, createdAt, and updatedAt.

        ## Workflow
        A versioned list of Tasks. Published versions are immutable.

        ## Task
        A unit of work. SERVICE_TASK is lightweight. BATCH_TASK is long-running and retryable.

        ## Execution
        A run instance with status, task executions, and output artifacts.

        ## Output Artifact
        Metadata for S3-like output files, preview, checksum, and idempotency key.

        ## Status Lifecycle
        Execution statuses: QUEUED, RUNNING, FAILED, COMPLETED, CANCELLED, PARTIAL_SUCCESS. Task statuses: PENDING, QUEUED, RUNNING, FAILED, COMPLETED, SKIPPED, RETRYING.

        ## Common Incidents
        Batch timeout, duplicate output, stuck RUNNING, preview OOM, partial completion undefined, invalid config upload, Athena preview timeout, and output permission denied.

        ## Cross-role Knowledge Asymmetry
        BA, TL, FE, BE, QA, and OPS each own different parts of the same behavior. DREAM connects them through evidence-backed Requirement Cases.
        """,
    )

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    section = """

    ## Demo Dataset: DemoCorp Forecast Platform

    DFP is a synthetic enterprise forecast and analytics platform for DREAM demos. It includes UI, Java backend, AWS-style orchestration, and Python processor layers. It also includes architecture docs, runbooks, incident history, Jira history, PR history, testing docs, concept memory, fake code, fake diffs, rough requirement requests, and representative outputs.

    The dataset is designed to demonstrate codebase-aware engineering memory across requirement intelligence, impact mapping, PR review, audit/eval, and codebase indexing. All data is synthetic and uses DemoCorp / DFP / ForecastDemo / BatchJobDemo naming only.

    Recommended demo flow:

    ```bash
    dream kb search --team demo_team --query "execution status stuck running"

    dream codebase index \\
      --team demo_team \\
      --repo examples/dfp-demo-repo \\
      --name dfp-demo-repo

    dream codebase search \\
      --team demo_team \\
      --repo dfp-demo-repo \\
      --query "status tracker batch task"

    dream req create \\
      --team demo_team \\
      --request "Users want to know which task is still running when a forecast job takes too long" \\
      --role BA

    dream req analyze --case <case_id>
    dream req impact --case <case_id>
    dream req questions --case <case_id> --role TL
    dream req brief --case <case_id>
    dream req jira --case <case_id>

    dream review pr \\
      --team demo_team \\
      --repo dfp-demo-repo \\
      --diff examples/pr-diffs/DFP-110-output-collector-idempotency.diff \\
      --jira knowledge_packs/demo_team/docs/historical-jira/DFP-110-output-collection-idempotency.md
    ```
    """
    section = dedent(section)
    if "## Demo Dataset: DemoCorp Forecast Platform" not in readme:
        readme = readme.replace("## Docker", section + "\n## Docker")
    else:
        start = readme.index("## Demo Dataset: DemoCorp Forecast Platform")
        end = readme.find("\n## ", start + 1)
        readme = readme[:start] + section.lstrip() + (readme[end:] if end != -1 else "")
    readme_path.write_text(readme, encoding="utf-8")


def main() -> None:
    build_team_yaml()
    build_knowledge_docs()
    build_codebase()
    build_examples_and_docs()


if __name__ == "__main__":
    main()
