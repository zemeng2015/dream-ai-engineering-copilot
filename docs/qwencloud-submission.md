<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Hackathon Submission Brief

## Project

**DREAM: Source-backed MemoryAgent for engineering teams**

DREAM turns scattered team knowledge, codebase structure, incidents, historical
Jira/PR context, raw document intake, and review decisions into governed memory
that a Qwen-backed agent can retrieve, cite, evaluate, and improve across
sessions.

## Track

Track 1: MemoryAgent

Why it fits:

- Persistent memory: knowledge packs, codebase indexes, intake documents,
  approved memory claims, conflict ledgers, audit records, and human ratings are
  durable across sessions.
- Better decisions over time: each scan, review, rating, and conflict resolution
  becomes reusable evidence for later requirement drafts and PR reviews.
- Limited context windows: retrieval returns compact context cards with source
  paths, matched terms, claim proof, and graph links instead of dumping whole
  documents into the prompt.
- Timely forgetting: conflicting or stale claims can be rejected, quarantined,
  or superseded through the governed ledger before they are used as trusted
  memory.

## Qwen Cloud Usage

DREAM includes a first-class `qwen-cloud` LLM provider that calls Qwen Cloud's
OpenAI-compatible endpoint with `DASHSCOPE_API_KEY`, `QWEN_BASE_URL`, and
`QWEN_MODEL`.

Default hackathon settings:

```text
provider: qwen-cloud
base_url: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
model: qwen3.7-plus
```

## Demo Flow

1. Start API and frontend.
2. Show `/health` proving Qwen Cloud mode and Alibaba Cloud deployment metadata.
3. Show `/qwencloud/showcase` proving the judge-facing Track 1 flow, evidence
   paths, and scorecard posture from the deployed backend.
4. Ingest or promote an engineering source document in Memory Hub.
5. Run memory scan and review claims.
6. Create a requirement case from a rough user ask.
7. Show context trail, impact map, role questions, Qwen-generated brief, and
   Jira-ready draft.
8. Show audit/eval record and human rating loop.

## Judging Alignment

Innovation and AI creativity:
DREAM is a governed memory layer for engineering decisions, not a stateless
chatbot. Memory is versioned, reviewed, evaluated, and traceable back to raw
source spans.

Technical depth and engineering:
FastAPI API, Typer CLI, Angular frontend, provider abstraction, codebase index,
evidence graph, memory distillation, conflict ledger, audit/eval store, tests,
Docker, and Alibaba Cloud Function Compute deployment proof.

Problem value and impact:
Engineering teams lose time because AI assistants forget local history,
misread code ownership, and hallucinate requirements. DREAM makes the agent
remember the team's actual docs, code, incidents, and prior decisions.

Presentation and docs:
Use `docs/qwencloud-architecture.md`, `docs/assets/qwencloud-architecture.svg`,
and `deploy/alibaba/README.md` for Devpost.

## Required Devpost Links

- Source code: public GitHub repository
- License: Apache-2.0
- Architecture diagram: `docs/assets/qwencloud-architecture.svg`
- Architecture upload asset: `docs/assets/qwencloud-architecture.png`
- Alibaba Cloud proof: `deploy/alibaba/serverless-devs.yaml`
- Deploy preflight: `scripts/qwencloud-deploy-preflight.ps1`
- Submission packet: `scripts/qwencloud-hackathon-submission-packet.ps1`
- Blog/social bonus draft: `docs/qwencloud-build-journey-post.md`
- Demo video: target under 3 minutes
