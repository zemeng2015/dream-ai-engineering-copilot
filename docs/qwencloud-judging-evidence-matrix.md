<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Judging Evidence Matrix

This matrix is the judge-facing index for the DREAM Qwen Cloud submission. It
separates evidence that is already present in the public repository from live
external proof that must be added at action time.

## Current Evidence Posture

| Area | Static repo evidence | Live external proof still required |
|---|---|---|
| Stage One and Qwen Cloud fit | Qwen provider, Qwen config, Track 1 submission brief, Alibaba deployment template | Deployed Alibaba backend URL |
| Innovation and AI Creativity | Memory distillation, context intelligence, knowledge packs, codebase retrieval, requirement generation, audit/eval | None |
| Technical Depth and Engineering | FastAPI, config/provider abstraction, Docker, CI, Alibaba release workflow, readiness and bundle gates | Deployed Alibaba backend URL |
| Problem Value and Impact | Devpost copy, requirement intelligence docs, PR review docs, open-core strategy, workflow tests | None |
| Presentation and Documentation | Architecture assets, demo script, captions, transcript, thumbnail, video renderer, judge rehearsal, Devpost payload tooling | Public demo video URL |

The `scripts/qwencloud-judging-scorecard.ps1` report treats criteria that depend
on the public video URL or deployed backend URL as DRAFT until those values are
real. That is intentional: the static evidence can be complete while the final
Devpost submission still waits for action-time publication and Alibaba proof.

## Criteria Evidence

### Stage One: baseline viability and required Qwen Cloud use

Claim: DREAM is submitted as Track 1 MemoryAgent and uses Qwen Cloud through the
`qwen-cloud` provider, Qwen config, and Alibaba Function Compute deployment
proof.

Static evidence:

- `examples/config/dream.qwen.yaml`
- `dream/api/routes.py`
- `dream/llm/qwen_cloud.py`
- `tests/test_qwen_cloud_provider.py`
- `deploy/alibaba/serverless-devs.yaml`
- `docs/qwencloud-submission.md`

External proof required:

- Public deployed backend URL returning `/health` with `llm_provider=qwen-cloud`
  and `deployment_target=alibaba-function-compute`.
- Public deployed backend URL returning `/qwencloud/showcase` with Track 1,
  Qwen Cloud, Alibaba runtime, judge-flow, and scorecard posture fields.

### Innovation and AI Creativity

Claim: DREAM combines persistent source-backed memory, claim review, retrieval
traces, requirement drafting, audit/eval feedback, and Qwen Cloud generation
instead of a one-shot chatbot prompt.

Static evidence:

- `dream/llm/qwen_cloud.py`
- `dream/memory/distiller.py`
- `dream/knowledge/pack_loader.py`
- `dream/context/service.py`
- `dream/codebase/retriever.py`
- `dream/requirements/generator.py`
- `docs/memory-distillation.md`
- `docs/context-intelligence-layer.md`
- `docs/evaluation-agent.md`

External proof required:

- None beyond final public repo availability.

### Technical Depth and Engineering

Claim: DREAM includes provider abstraction, API/CLI surfaces, Docker packaging,
Alibaba custom container deployment, CI, proof automation, final readiness
gates, and deterministic local verification.

Static evidence:

- `dream/api/app.py`
- `dream/api/routes.py`
- `dream/core/config.py`
- `dream/config/loader.py`
- `Dockerfile`
- `.github/workflows/ci.yml`
- `.github/workflows/qwencloud-release.yml`
- `scripts/qwencloud-run-local-proof.sh`
- `scripts/qwencloud-final-readiness.ps1`
- `scripts/qwencloud-final-upload-bundle.ps1`
- `scripts/qwencloud-live-inputs-intake.ps1`
- `scripts/qwencloud-official-rules-gate.ps1`
- `docs/qwencloud-architecture.md`
- `docs/assets/qwencloud-architecture.png`

External proof required:

- Public deployed backend URL.
- `/qwencloud/showcase` reachable from that backend URL.
- Alibaba screenshot and backend proof recording in the final upload bundle.

### Problem Value and Impact

Claim: DREAM targets engineering teams that lose context across tickets, source,
incidents, and review history, then turns that context into auditable requirement
and review outputs with reusable governed memory.

Static evidence:

- `docs/qwencloud-devpost-form-fields.md`
- `docs/requirement-intelligence.md`
- `docs/pr-review.md`
- `docs/open-core-strategy.md`
- `tests/test_requirement_cases.py`
- `tests/test_pr_review.py`
- `tests/test_codebase_memory.py`

External proof required:

- None beyond final public repo availability.

### Presentation and Documentation

Claim: The repo includes architecture SVG/PNG, a rendered demo-video pipeline,
official-source refresh, video upload handoff, Devpost field payloads, final
action board, and upload bundle manifests.

Static evidence:

- `docs/assets/qwencloud-architecture.svg`
- `docs/assets/qwencloud-architecture.png`
- `docs/assets/qwencloud-video-thumbnail.svg`
- `docs/assets/qwencloud-video-thumbnail.png`
- `docs/qwencloud-demo-video-script.md`
- `docs/qwencloud-demo-video-captions.srt`
- `docs/qwencloud-demo-video-transcript.md`
- `scripts/qwencloud-frontend-build-proof.ps1`
- `scripts/qwencloud-render-demo-video.ps1`
- `scripts/qwencloud-export-video-thumbnail.ps1`
- `scripts/qwencloud-video-publication-handoff.ps1`
- `scripts/qwencloud-video-upload-status.ps1`
- `scripts/qwencloud-devpost-draft-payload.ps1`
- `scripts/qwencloud_seed_demo_artifact.py`
- `scripts/qwencloud-judge-rehearsal.ps1`
- `scripts/qwencloud-final-external-handoff.ps1`
- `frontend/src/app/features/hackathon-demo/hackathon-demo.component.ts`
- `frontend/src/app/features/hackathon-demo/hackathon-demo.component.html`
- `frontend/src/app/features/hackathon-demo/hackathon-demo.component.spec.ts`
- `docs/qwencloud-video-upload-handoff.md`
- `docs/qwencloud-official-requirements-snapshot.md`
- `docs/qwencloud-devpost-submission-kit.md`
- `scripts/qwencloud-official-source-refresh.ps1`

External proof required:

- Public demo video URL on a Devpost-accepted platform.

## Final Use

Before final submit, run:

```powershell
scripts/qwencloud-judging-scorecard.ps1 `
  -DemoVideoUrl "<public-video-url>" `
  -BackendUrl "<deployed-backend-url>"
```

Expected final state:

- `readyForJudgingNarrative=true`
- `weightedEvidenceReady=100`
- `weightedStaticEvidenceReady=100`
- `missingRequiredCriteria=[]`
