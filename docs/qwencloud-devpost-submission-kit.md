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
  - `docs/assets/qwencloud-architecture.png`
  - `scripts/qwencloud-capture-alibaba-proof.ps1`
  - `docs/qwencloud-build-journey-post.md`
  - `deploy/alibaba/serverless-devs.yaml`
  - `deploy/alibaba/README.md`

## 2) Track and Technical Promise

Required track:

- Track 1: MemoryAgent

Suggested Description points (copy into Devpost):

- DREAM uses Qwen Cloud as the memory-grounded generation layer.
- Inputs include knowledge packs, codebase index, incidents, PR context, and approved memory claims.
- Outputs are traceable and reviewable, and memory improves through audit/eval feedback.
- `/health` proves runtime mode, model, deployment target, and proof file.

## 3) Demo Video (Under 3 Minutes)

Use `docs/qwencloud-demo-video-script.md` for narration and render the local
upload file with:

```powershell
scripts/qwencloud-render-demo-video.ps1
```

Expected local upload file:

`artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`

Recommended 4-shot order:

1. `/health` proof (Track, provider, model, region, proof file).
2. Memory Hub intake and claim review.
3. Requirement case flow (prompt -> impact map -> brief -> Jira draft).
4. Audit/eval and manual scoring.

## 4) Deployability Proof

Use `deploy/alibaba/README.md`.

Run preflight before a real deployment:

```powershell
scripts/qwencloud-deploy-preflight.ps1 -BuildImage -SmokeContainer
```

Required proof artifacts:

- FC build/deploy success output or screenshot.
- Devpost screenshot from:
  `scripts/qwencloud-capture-alibaba-proof.ps1 -BaseUrl "https://<function-compute-endpoint>"`
- `curl` or browser result from `/health`.
- One successful `POST /requirements/draft` response.

## 5) Devpost Copy (Optional Paste-ready)

Generate the packet after the deployed backend and public video URLs are ready:

```powershell
scripts/qwencloud-hackathon-submission-packet.ps1 `
  -RepoUrl "https://github.com/zemeng2015/dream-ai-engineering-copilot" `
  -DemoVideoUrl "https://www.youtube.com/..." `
  -BackendUrl "https://<function-compute-endpoint>"
```

### Project Title

`DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence`

### One-minute Pitch

Engineering teams lose critical context when switching between tickets, code, incidents, and reviews.
DREAM turns these artifacts into governed, source-backed memory so Qwen Cloud can
produce traceable requirement and review outputs instead of one-shot chat answers.

### What it does

- Maintains durable engineering memory from docs, codebase, incidents, PRs, and approved claims.
- Uses OpenAI-compatible Qwen Cloud APIs in a governed retrieval flow.
- Adds audit/eval/ratings to improve memory quality over time.

### Why it matters

- Reduces hallucination by grounding outputs with local source evidence.
- Improves team continuity with role-aware, context-based requirement drafting.
- Keeps secrets in environment variables; only status flags are exposed in health outputs.

## 6) Final 30-minute Submission Run

1. Fill in Devpost fields (project, description, links).
2. Attach `docs/assets/qwencloud-architecture.png`,
   `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`, and the
   under-3-minute video.
3. Add public repo link and Apache-2.0 license.
4. Generate `scripts/qwencloud-hackathon-submission-packet.ps1` with real URLs.
5. Run `docs/qwencloud-live-checklist.md` items 1-6 quickly.
6. Add optional blog/social link if `docs/qwencloud-build-journey-post.md` was published.
7. Submit only after the external Devpost form shows accepted URLs.

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
- `scripts/qwencloud-capture-alibaba-proof.ps1`
- `scripts/qwencloud-export-architecture-png.ps1`
