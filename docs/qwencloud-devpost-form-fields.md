<!-- SPDX-License-Identifier: Apache-2.0 -->

# Devpost Form Draft (Track 1 MemoryAgent)

This is a copy-ready draft you can paste into Devpost fields.

## Project name

DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence

## Team name

Use your preferred team / handle.

## Description

### Problem

Engineering teams often lose context across tickets, codebases, incidents, and past
reviews. AI assistants then answer from memoryless prompts, which causes hallucination,
inconsistent requirements, and repeated onboarding.

### What we built

DREAM is a source-backed MemoryAgent for engineering workflows. It unifies:

- Knowledge packs (runbooks, incidents, architecture docs, historical Jira/PR context)
- Codebase memory (files, symbols, concepts, tests, relationships)
- Governed memory claims with human approval/rejection and conflict resolution
- Audit/evaluation/rating feedback to improve future outputs
- Qwen Cloud generation via OpenAI-compatible endpoint

The workflow is traceable and production-minded: every generated answer is tied to
retrieved evidence and can be audited later.

### Technical stack

- FastAPI + Typer backend with provider abstraction
- OpenAI-compatible Qwen Cloud adapter (`qwen-cloud`)
- Angular workbench and engineering workflow APIs
- SQLite-based audit and eval ledgers
- Docker + Alibaba Cloud Function Compute custom container deployment

### Why this is Track 1

It is a MemoryAgent: the core value is durable, reviewable memory that improves
decision quality across requirement drafting, PR review, and engineering workflows.

## Video link

Render and upload the <3-minute demo video:

```powershell
scripts/qwencloud-render-demo-video.ps1
```

Local upload file:

`artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`

The video covers:

1) /health proof (Track 1 + qwen-cloud + model + proof file)
2) Memory Hub intake + claim review
3) Requirement case to brief/Jira draft
4) Audit/eval with a human rating action

## Add these links in description or resources section

- Source code: (public GitHub repository)
- License: Apache-2.0
- Architecture diagram: `docs/assets/qwencloud-architecture.svg`
- Deployment proof: `deploy/alibaba/serverless-devs.yaml`
- Qwen mode entry: `examples/config/dream.qwen.yaml`

## Notes

- Keep secrets off every public field.
- Mention `DREAM with qwen-cloud`, `Track 1 MemoryAgent`, and `Alibaba Cloud Function Compute` in description.
- If live Qwen endpoints are temporarily unstable, include fallback plan in demo narrative
  while still showing governance, memory scan, and `/health` verification.
