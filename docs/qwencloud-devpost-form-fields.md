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
- Architecture PNG upload asset: `docs/assets/qwencloud-architecture.png`
- Deployment proof: `deploy/alibaba/serverless-devs.yaml`
- Qwen mode entry: `examples/config/dream.qwen.yaml`
- Optional blog/social draft: `docs/qwencloud-build-journey-post.md`

## Additional info form

These fields were checked against the live Devpost draft for the Qwen Cloud
hackathon.

- Submitter type: `Individual`
- Organization name: leave blank
- Country of residence: `United States`
- Newly built or previously existing project: `New`
- Project start date: `06-21-26`
- If started/existed before May 26: `Not applicable. The public DREAM memory platform release started on 06-21-26; Qwen Cloud Track 1 integration, Alibaba packaging, CI audit, architecture assets, and demo/submission materials were added during the hackathon submission period.`
- Track: `Track 1: MemoryAgent`
- Code repository URL: `https://github.com/zemeng2015/dream-ai-engineering-copilot`
- Alibaba Cloud deployment proof code file: `https://github.com/zemeng2015/dream-ai-engineering-copilot/blob/main/deploy/alibaba/serverless-devs.yaml`
- Architecture diagram upload: `docs/assets/qwencloud-architecture.png`
- Alibaba deployment screenshot upload: `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`
- Blog/social journey URL: optional; use a published copy of `docs/qwencloud-build-journey-post.md` if available
- AI tools leveraged: `Qwen Cloud for the runtime LLM provider, OpenAI Codex for implementation assistance, GitHub Actions for CI verification, and local automation scripts for audit, render, deploy preflight, and submission packet generation.`
- Learning level: `Significant`

## Notes

- Keep secrets off every public field.
- Mention `DREAM with qwen-cloud`, `Track 1 MemoryAgent`, and `Alibaba Cloud Function Compute` in description.
- If live Qwen endpoints are temporarily unstable, include fallback plan in demo narrative
  while still showing governance, memory scan, and `/health` verification.
