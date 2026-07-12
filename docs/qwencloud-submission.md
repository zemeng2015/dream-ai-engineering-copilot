<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Hackathon Submission Brief

## Project

**DREAM: Qwen-curated experience memory for engineering teams**

DREAM gives Qwen durable experience across sessions without letting old,
expired, or explicitly forgotten guidance leak back into context. Qwen curates
preferences, policies, and reusable lessons; DREAM enforces lifecycle state,
limited-context recall, provenance, and feedback. The same memory layer can
ground engineering artifacts in approved docs, code, incidents, and decisions.

## Track

Track 1: MemoryAgent

Why it fits:

- Persistent memory: Qwen decides whether an observation is a durable
  preference, operating policy, reusable episode, or noise.
- Better decisions over time: explicit helpful/correct feedback changes future
  ranking, while every curator decision remains auditable.
- Limited context windows: recall ranks current memory into a hard token budget
  and emits a compact context card.
- Timely forgetting: newer conflicts supersede old values, TTL expires temporary
  guidance, and explicit forget requests remove memory from future recall.
- Source-backed grounding: approved MemoryClaims retain reviewer identity and
  underlying source paths before they can influence generated artifacts.

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
`ap-southeast-1`, `Alibaba Cloud Function Compute custom runtime`, durable
`tablestore` storage, and `partition-local-transaction` mode. The exact public
runtime build is `cb6255b7a1565a631daec6215bd146f495d97df8`; benchmark claims
below intentionally make no latency comparison.

## Alibaba Cloud Durability Proof

- One real Qwen-curated memory survived a same-source redeploy onto a different
  Function Compute instance with the same memory ID, decision ID, and Qwen
  provider request ID.
- Twenty simultaneous public conflicting writes completed 20/20 with no errors
  or 429s. Tablestore retained one active truth and 19 superseded histories.
- Function Compute supplies temporary credentials through a narrow RAM execution
  role; no deployment AccessKey is present in function configuration.

Sanitized evidence:

- `docs/assets/qwencloud-fc-persistence-proof-summary.json`
- `docs/assets/qwencloud-fc-http-contention-proof-summary.json`
- `docs/qwencloud-fc-runtime-proof.md`

## Experience Lifecycle Benchmark

A real Qwen Cloud run executed 37 curator decisions across 24 synthetic
cross-session cases. The dataset covers durable preferences, conflict
supersession, TTL and explicit forgetting, duplicate rejection, and limited
token budgets.

| Metric | Result |
|---|---:|
| Lifecycle cases passed | 24/24 |
| Qwen proposal accuracy | 100% |
| Governed action accuracy | 100% |
| Critical-memory recall | 100% |
| Forbidden-memory leak | 0% |
| Token-budget compliance | 100% |
| Weighted score | 100.0/100 |

The benchmark uses synthetic scenarios and one Qwen curator decision per step;
it does not establish production effectiveness. The public dataset, runner,
methodology, summary, and per-step report are in
`examples/experience-benchmark/scenarios.yaml`,
`scripts/qwencloud_experience_memory_benchmark.py`, and
`docs/qwen-experience-memory-benchmark.md`.

## Paired Grounding Benchmark

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

1. Open `/hackathon-demo`; `/health` proves Qwen Cloud and Alibaba runtime identity.
2. Run the live three-session Arena.
3. Show Qwen return `remember`, then `supersede` for a conflicting preference.
4. Show Session 3 recall the current value in 19/64 tokens with old-value leak `no`.
5. Show the same memory, decision, and Qwen receipt after an FC instance change.
6. Show 20/20 conflicting public writes leaving one active truth and 19 histories.
7. Show the transparently scoped paired benchmark, lifecycle suite, and deployed
   Qwen Cloud + Function Compute + Tablestore architecture.

## Judging Alignment

Innovation and AI creativity:
DREAM combines a Qwen semantic memory curator with deterministic lifecycle
governance. The live demo proves cross-session conflict handling and constrained
recall instead of presenting another stateless chatbot.

Technical depth and engineering:
FastAPI API, Angular Judge Arena, Qwen structured decisions, transactional
Alibaba Tablestore lifecycle state, feedback ranking, token-budget recall,
scoped temporary RAM credentials, benchmark runner, tests, and Alibaba Function
Compute cross-instance deployment proof.

Problem value and impact:
Engineering teams lose time because AI assistants forget local history,
misread code ownership, and hallucinate requirements. DREAM makes the agent
remember the team's actual docs, code, incidents, and prior decisions.

Presentation and docs:
Use `docs/qwencloud-architecture.md`, `docs/assets/qwencloud-architecture.svg`,
and `deploy/alibaba/README.md` for Devpost.

## Required Devpost Links

- Source code: <https://github.com/zemeng2015/dream-ai-engineering-copilot/tree/codex/champion-memory-loop>
- Live demo: `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/`
- License: Apache-2.0
- Architecture diagram: `docs/assets/qwencloud-architecture.svg`
- Architecture upload asset: `docs/assets/qwencloud-architecture.png`
- Alibaba Cloud proof: `deploy/alibaba/serverless-devs-runtime.yaml`
- Deploy preflight: `scripts/qwencloud-deploy-preflight.ps1`
- Submission packet: `scripts/qwencloud-hackathon-submission-packet.ps1`
- Published build journey: <https://zemeng2015.github.io/dream-ai-engineering-copilot/qwencloud-build-journey-post.html>
- Demo video: target under 3 minutes
