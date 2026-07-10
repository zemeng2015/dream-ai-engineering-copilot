# SPDX-License-Identifier: Apache-2.0

# Qwen Cloud Demo Video Script

Target length: 2:15 to 2:45.

## 0:00 - 0:20 Opening and Problem

Engineering teams often ask AI for help, but existing context is scattered across
tickets, runbooks, code, PRs, incidents, and past decisions. The AI often
forgets this history. DREAM turns this into durable, governed memory.

Open `/hackathon-demo` first to frame the judge flow and show the Track 1,
Qwen Cloud, local proof, and remaining external submission gates.

## 0:20 - 0:45 Architecture Proof

Show `docs/assets/qwencloud-architecture.svg`, then open `/health` and
`/qwencloud/showcase`.

Call out:

- Track is `Track 1: MemoryAgent`.
- Provider is `qwen-cloud`.
- Model is `qwen3.7-plus`.
- Deployment target is Alibaba Cloud Function Compute custom runtime.
- `/health` never exposes secrets.
- `/qwencloud/showcase` exposes the judge-facing flow, evidence paths, and
  scorecard posture without exposing secrets.

## 0:45 - 1:20 Memory Intake and Review

Use the `/hackathon-demo` Start Memory entry, then show:

- raw source document intake
- parsed sections with source spans
- claim review queue
- approve or quarantine one claim
- ledger evidence that only reviewed memory is reusable

## 1:20 - 1:55 Requirement Case Flow

Create a requirement case from:

```text
Users need to know why a forecast job is stuck running and which downstream
outputs are blocked.
```

Show:

- retrieved context from docs, codebase, incidents, and approved claims
- impact map
- role-specific clarification questions
- Qwen-generated engineering brief
- Jira-ready draft

## 1:55 - 2:20 Product Walkthrough and Audit

Open Audit/Eval:

- run id and scoring dimensions
- source paths used
- source-backed explanation links
- one human rating interaction

## 2:20 - 2:45 Submission Proof and Close

DREAM is a Qwen Cloud MemoryAgent for engineering teams: it remembers source truth,
retrieves the right context, quarantines stale memory, and improves future outputs
through audit and evaluation.

