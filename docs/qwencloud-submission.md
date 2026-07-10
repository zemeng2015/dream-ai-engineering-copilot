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
OpenAI-compatible endpoint using environment-based `DASHSCOPE_API_KEY`,
`QWEN_BASE_URL`, and `QWEN_MODEL` configuration. Credential values and the
dedicated workspace endpoint are kept private and are not included in
submission materials.

The public Function Compute deployment uses Alibaba's official shared Singapore
endpoint with the same workspace key and `qwen3.7-plus`; this endpoint is public
configuration, while the key and dedicated workspace URL remain private.

Default hackathon settings:

```text
provider: qwen-cloud
model: qwen3.7-plus
```

## Live Demo

- Workbench: <https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/>
- Judge route: <https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/hackathon-demo>
- Health proof: <https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/health>
- Showcase: <https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/qwencloud/showcase>

The deployed runtime reports `qwen-cloud`, `qwen3.7-plus`,
`ap-southeast-1`, and `Alibaba Cloud Function Compute custom runtime`. The
automated live gate also requires a non-empty Qwen-generated requirement draft;
the paired benchmark below intentionally makes no latency claim.

## Paired Benchmark Evidence

A real Qwen Cloud run compared a stateless baseline with Qwen + DREAM across
seven paired synthetic engineering cases. Both arms used `qwen3.7-plus` at
temperature `0` with the same output contract and deterministic reference
scorer; the changed variable was organization evidence absent versus
DREAM-retrieved evidence.

| Metric | Baseline | Qwen + DREAM | Delta |
|---|---:|---:|---:|
| Mean deterministic reference score | 25.3 | 48.7 | +23.4 |
| Unsupported references | 0 | 0 | 0 |

DREAM scored higher in `7/7` paired cases, with exact paired permutation
`p=0.0156`. Exact retrieval Recall@12 was `35.6%` and remains a bottleneck.

The result is evidence for this seven-case synthetic benchmark, not a claim of
production effectiveness. It uses one deterministic completion per arm, and
the exact-term scorer does not measure semantic equivalence. Latency/token
sidecars are incomplete, so no latency or token comparison is made. The
machine-readable summary is
`docs/assets/qwen-memory-ab-benchmark-summary.json`; the public methodology and
per-case table are in `docs/qwen-memory-ab-benchmark.md`.

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
- Live demo: `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/`
- License: Apache-2.0
- Architecture diagram: `docs/assets/qwencloud-architecture.svg`
- Architecture upload asset: `docs/assets/qwencloud-architecture.png`
- Alibaba Cloud proof: `deploy/alibaba/serverless-devs-runtime.yaml`
- Deploy preflight: `scripts/qwencloud-deploy-preflight.ps1`
- Submission packet: `scripts/qwencloud-hackathon-submission-packet.ps1`
- Blog/social bonus draft: `docs/qwencloud-build-journey-post.md`
- Demo video: target under 3 minutes
