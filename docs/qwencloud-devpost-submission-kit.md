<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Hackathon Submission Kit

Use this checklist to finish Devpost submission end-to-end.

## 1) Repo and License Readiness

- Public GitHub repository link is accessible.
- Root `LICENSE` is `Apache-2.0`.
- Use this repo/branch as the submission reference.
- Required files are present:
  - `docs/qwencloud-submission.md`
  - `docs/qwencloud-architecture.md`
  - `docs/qwencloud-demo-video-script.md`
  - `docs/qwencloud-demo-video-captions.srt`
  - `docs/qwencloud-demo-video-transcript.md`
  - `docs/qwencloud-video-upload-handoff.md`
  - `docs/qwencloud-official-requirements-snapshot.md`
  - `docs/qwencloud-judging-evidence-matrix.md`
  - `docs/qwencloud-testing-and-rights-notes.md`
  - `docs/qwen-experience-memory-benchmark.md`
  - `docs/assets/qwen-experience-memory-benchmark-summary.json`
  - `docs/assets/qwen-experience-memory-benchmark-report.json`
  - `docs/assets/qwencloud-architecture.png`
  - `examples/experience-benchmark/scenarios.yaml`
  - `scripts/qwencloud_experience_memory_benchmark.py`
  - `scripts/qwencloud-alibaba-runtime-release.ps1`
  - `scripts/qwencloud-run-local-proof.ps1`
  - `scripts/qwencloud-run-local-proof.sh`
  - `scripts/qwencloud_seed_demo_artifact.py`
  - `scripts/qwencloud-judge-rehearsal.ps1`
  - `scripts/qwencloud-capture-alibaba-proof.ps1`
  - `scripts/qwencloud-render-alibaba-proof-video.ps1`
  - `scripts/qwencloud-cloud-credentials-handoff.ps1`
  - `scripts/qwencloud-devpost-handoff.ps1`
  - `scripts/qwencloud-devpost-autofill-snippet.ps1`
  - `scripts/qwencloud-devpost-materials-audit.ps1`
  - `scripts/qwencloud-final-readiness.ps1`
  - `scripts/qwencloud-final-upload-bundle.ps1`
  - `scripts/qwencloud-final-external-handoff.ps1`
  - `scripts/qwencloud-official-source-refresh.ps1`
  - `scripts/qwencloud-official-rules-gate.ps1`
  - `scripts/qwencloud-deadline-guard.ps1`
  - `scripts/qwencloud-live-inputs-intake.ps1`
  - `scripts/qwencloud-github-ci-proof.ps1`
  - `scripts/qwencloud-frontend-build-proof.ps1`
  - `frontend/src/app/features/hackathon-demo/hackathon-demo.component.ts`
  - `docs/qwencloud-build-journey-post.md`
  - `deploy/alibaba/serverless-devs-runtime.yaml`
  - `deploy/alibaba/README.md`

## 2) Track and Technical Promise

Required track:

- Track 1: MemoryAgent

Suggested Description points (copy into Devpost):

- DREAM uses Qwen Cloud as the memory-grounded generation layer.
- Qwen curates cross-session experience into remember, supersede, forget, or
  ignore decisions; DREAM enforces TTL, lifecycle state, token budgets, and feedback.
- Inputs include knowledge packs, codebase index, incidents, PR context, and approved memory claims.
- Outputs are traceable and reviewable, and memory improves through audit/eval feedback.
- `/health` proves runtime mode, model, deployment target, and proof file.
- `/qwencloud/showcase` proves the judge-facing Track 1 flow, evidence paths,
  and scorecard posture from the deployed backend.

## 3) Demo Video (Under 3 Minutes)

Use `docs/qwencloud-demo-video-script.md` for narration and render the local
upload file with:

```powershell
scripts/qwencloud-render-demo-video.ps1
scripts/qwencloud-video-publication-handoff.ps1
```

Expected local upload file:

`artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`

Matching first-impression assets:

- YouTube thumbnail: `docs/assets/qwencloud-video-thumbnail.png`
- Devpost gallery: `artifacts/qwencloud-proof/video-v3/devpost-gallery-v3/`
- Gallery manifest: `devpost-gallery-v3/gallery-v3-manifest.json`
- Canonical Devpost story: `docs/qwencloud-devpost-story.md`

Regenerate both from the V3-only Remotion entry with:

```powershell
cd tools/submission-video-v2
npm run gallery:v3
```

Use `docs/qwencloud-video-upload-handoff.md` plus the latest
`video-publication-handoff-*.md` report for the public upload title,
description, accepted video platforms, visibility check, local MP4 SHA256,
caption SHA256, and Chrome file upload troubleshooting.

V3 story order:

1. Make the stale-memory failure concrete: the rollout changed from 10% to 20%,
   but an agent can still recall 10%.
2. Run `/hackathon-demo` continuously: remember -> supersede -> fresh-session
   recall, with Qwen receipts, one active truth, 19/64 tokens, and no old-value leak.
3. Show the cloud proof: the same memory, decision, and Qwen receipt survive a
   Function Compute instance replacement; 20/20 public conflicting writes leave
   one active truth and 19 historical versions.
4. Close with the transparently limited synthetic benchmark and the deployed
   Qwen Cloud + Function Compute + Tablestore + RAM-role architecture.

## 4) Deployability Proof

Use `deploy/alibaba/README.md`.

Record a local Angular build proof for the demo UI:

```powershell
scripts/qwencloud-frontend-build-proof.ps1
```

Open the judge-facing Angular route for the first screen of the demo:

```text
http://localhost:4300/hackathon-demo
```

When the API is running on `http://127.0.0.1:8000`, this page runs three real
Qwen-backed memory sessions and shows the lifecycle ledger beside live
`/health` and benchmark evidence. When the API is not running, the benchmark
and deep evidence routes remain available.

Run preflight before a real deployment:

```powershell
Copy-Item .env.qwencloud.local.example .env.qwencloud.local
# Fill .env.qwencloud.local locally. It is ignored by git.
scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft
scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer -AllowDraft
```

Run local proof without manually opening a second shell:

```powershell
scripts/qwencloud-run-local-proof.ps1
```

Linux/macOS or Bash runner:

```bash
bash scripts/qwencloud-run-local-proof.sh --skip-draft
```

Generate an optional seeded judge demo package so approved memory search/context
is available before a manual claim-review walkthrough:

```powershell
python scripts/qwencloud_seed_demo_artifact.py --promote-count 6
```

Run a one-command judge rehearsal dashboard before recording the final demo:

```powershell
scripts/qwencloud-judge-rehearsal.ps1 -AllowDraft
```

Use `docs/qwencloud-judging-evidence-matrix.md` with the latest
`judging-scorecard-*.md` report to keep the Devpost narrative aligned with the
actual static evidence and the remaining live URL/proof gates.

Or use the full release orchestrator after credentials, registry login, and
video URL are ready:

```powershell
scripts/qwencloud-alibaba-runtime-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..."
```

Required proof artifacts:

- FC build/deploy success output or screenshot.
- Devpost screenshot from:
  `scripts/qwencloud-capture-alibaba-proof.ps1 -BaseUrl "https://<function-compute-endpoint>"`
- Separate Alibaba backend proof recording from:
  `scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl "https://<function-compute-endpoint>"`
- `curl` or browser result from `/health`.
- `curl` or browser result from `/qwencloud/showcase`.

## 5) Devpost Copy (Optional Paste-ready)

Generate the packet after the deployed backend and public video URLs are ready:

```powershell
scripts/qwencloud-hackathon-submission-packet.ps1 `
  -RepoUrl "https://github.com/zemeng2015/dream-ai-engineering-copilot" `
  -DemoVideoUrl "https://www.youtube.com/..." `
  -BackendUrl "https://<function-compute-endpoint>"
```

Generate a local browser handoff with copy fields, blockers, and upload paths:

```powershell
scripts/qwencloud-devpost-handoff.ps1 -AllowDraft
```

Generate a local browser-console autofill snippet for non-legal public text
fields:

```powershell
scripts/qwencloud-devpost-autofill-snippet.ps1 -AllowDraft
```

Audit the packet, draft payload, handoff, and autofill snippet together before
saving Devpost draft fields:

```powershell
scripts/qwencloud-devpost-materials-audit.ps1 `
  -DemoVideoUrl "https://www.youtube.com/..." `
  -BackendUrl "https://<function-compute-endpoint>"
```

### Project Title

`DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence`

### One-minute Pitch

Engineering teams lose critical context when switching between tickets, code, incidents, and reviews.
DREAM gives Qwen governed cross-session experience: it remembers durable
defaults, supersedes conflicts, forgets temporary or invalid guidance, recalls
the current truth under a hard context budget, and grounds later engineering
outputs in approved sources.

### What it does

- Maintains Qwen-curated preferences, policies, and reusable episodes across sessions.
- Enforces conflict supersession, TTL, explicit forgetting, and limited-context recall.
- Uses OpenAI-compatible Qwen Cloud APIs in a governed retrieval flow.
- Adds audit/eval/ratings to improve memory quality over time.

### Why it matters

- Reduces hallucination by grounding outputs with local source evidence.
- Improves team continuity with role-aware, context-based requirement drafting.
- Keeps secrets in environment variables; only status flags are exposed in
  health and showcase outputs.

## 6) Final 30-minute Submission Run

1. Fill in Devpost fields (project, description, links).
2. Attach `docs/assets/qwencloud-architecture.png`,
   `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`,
   `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4`, and the
   under-3-minute demo video.
3. Add public repo link and Apache-2.0 license.
4. Generate `scripts/qwencloud-hackathon-submission-packet.ps1` with real URLs
   and confirm it reports `READY`.
5. Run `scripts/qwencloud-devpost-materials-audit.ps1` with real URLs and
   confirm public copy, upload paths, and legal/external-write boundaries are
   `READY`.
6. Run `scripts/qwencloud-official-rules-gate.ps1` with real URLs and confirm
   it reports `READY`.
   Run `scripts/qwencloud-official-source-refresh.ps1` first if you want a
   fresh Devpost overview/rules source report in the final bundle.
7. Run `scripts/qwencloud-final-readiness.ps1` with real URLs and confirm it
   reports `READY`.
8. Run `scripts/qwencloud-final-upload-bundle.ps1` with real URLs and keep the
   generated zip nearby for upload fields, the Devpost handoff HTML, and manual
   review. Use the bundled `devpost-autofill-snippet-*.js` only for non-legal
   public text/link fields after action-time confirmation.
9. Run `scripts/qwencloud-final-external-handoff.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -AllowDraft`
   and keep the generated `external-handoff-*.zip` as the final action-time
   handoff for accounts, secrets, uploads, deployment, and legal submit.
10. Run `docs/qwencloud-live-checklist.md` items 1-6 quickly.
11. Add optional blog/social link if `docs/qwencloud-build-journey-post.md` was published.
12. Submit only after the external Devpost form shows accepted URLs.

## 7) Reproducibility Commands

```powershell
$env:DREAM_CONFIG_FILE="examples/config/dream.qwen.yaml"
$env:DASHSCOPE_API_KEY="<your-qwen-cloud-api-key>"

dream llm smoke --provider qwen-cloud --prompt "Return DREAM_QWEN_OK and one short phrase."
uvicorn dream.api.app:app --reload --host 127.0.0.1 --port 8000
```

Run helper scripts as needed:

- `scripts/qwencloud-hackathon-smoke.ps1`
- `scripts/qwencloud-hackathon-verify.ps1`
- `scripts/qwencloud-hackathon-proof.ps1`
- `scripts/qwencloud-hackathon-submit-gate.ps1`
- `scripts/qwencloud-hackathon-submission-packet.ps1`
- `scripts/qwencloud-alibaba-runtime-release.ps1`
- `scripts/qwencloud-run-local-proof.ps1`
- `scripts/qwencloud-run-local-proof.sh`
- `scripts/qwencloud-capture-alibaba-proof.ps1`
- `scripts/qwencloud-render-alibaba-proof-video.ps1`
- `scripts/qwencloud-frontend-build-proof.ps1`
- `scripts/qwencloud-deadline-guard.ps1`
- `scripts/qwencloud-live-inputs-intake.ps1`
- `scripts/qwencloud-github-ci-proof.ps1`
- `scripts/qwencloud-final-readiness.ps1`
- `scripts/qwencloud-final-upload-bundle.ps1`
- `scripts/qwencloud-export-architecture-png.ps1`
