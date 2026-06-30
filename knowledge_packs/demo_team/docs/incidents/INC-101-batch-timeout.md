<!-- SPDX-License-Identifier: Apache-2.0 -->

---
title: "Batch timeout"
doc_type: "incident"
team_id: "demo_team"
app: "ForecastDemo"
component: "incident-history"
concepts:
  - INC-101
  - batch timeout
  - operator
related_jira:
  - DFP-102
  - DFP-111
related_pr:
  - PR-501
related_incidents:
  - INC-101
---

    # Incident

    ## Summary
    INC-101: A BATCH_TASK exceeded configured timeout. Execution stayed RUNNING for too long. Operator had to inspect logs and manually mark task failed.

    ## Timeline
    - 09:05 Analyst reported unexpected ForecastDemo behavior.
    - 09:12 Operator found the affected Execution and TaskExecution.
    - 09:25 TL confirmed cross-layer impact.
    - 09:45 Temporary mitigation was applied in the synthetic demo environment.
    - 10:30 Follow-up Jira and PR review notes were created.

    ## Impact
    Analysts could not confidently determine whether forecast outputs were safe to preview or download. Operators spent extra time correlating Execution status, task logs, and output artifacts.

    ## Root Cause
    BatchJobAdapter did not emit a terminal timeout event into StatusTracker.

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
    - backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java
- backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java
- frontend/src/app/execution/execution-monitor.component.ts

    ## Related Jira
    - DFP-102
- DFP-111

    ## Related PRs
    - PR-501

    ## Regression Tests
    Add deterministic tests for the status, retry, output, permission, or preview branch that triggered INC-101.
