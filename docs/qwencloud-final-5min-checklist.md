# SPDX-License-Identifier: Apache-2.0

# Final 5-minute Checklist Before Devpost Submit

## Step 1 - Runtime proof (about 1 minute)

- Start API in qwen mode:

```powershell
$env:DREAM_CONFIG_FILE="examples/config/dream.qwen.yaml"
$env:DASHSCOPE_API_KEY="<key>"
$env:QWEN_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
python -m dream.cli.main llm smoke --provider qwen-cloud
uvicorn dream.api.app:app --reload --host 127.0.0.1 --port 8000
```

- In another shell:

```powershell
scripts/qwencloud-hackathon-verify.ps1 -BaseUrl http://localhost:8000
scripts/qwencloud-hackathon-submit-gate.ps1 -BaseUrl http://localhost:8000
```

One-command local alternative:

```powershell
scripts/qwencloud-run-local-proof.ps1
```

- Confirm output includes:
  - `llm_provider: qwen-cloud`
  - `track: Track 1: MemoryAgent`
  - `proof_file: deploy/alibaba/serverless-devs.yaml`

## Step 2 - Artifact evidence (about 1 minute)

- Confirm these are in repo:
  - `docs/qwencloud-submission.md`
  - `docs/qwencloud-architecture.md`
  - `docs/assets/qwencloud-architecture.svg`
  - `docs/assets/qwencloud-architecture.png`
  - `docs/qwencloud-demo-video-script.md`
  - `docs/qwencloud-build-journey-post.md`
  - `deploy/alibaba/serverless-devs.yaml`
  - `deploy/alibaba/README.md`
  - `docs/qwencloud-devpost-form-fields.md`

- Capture one screenshot of `/health` response and one screenshot of
  `POST /requirements/draft` success.
- Also capture one proof bundle:

```powershell
scripts/qwencloud-hackathon-proof.ps1 -BaseUrl http://localhost:8000
scripts/qwencloud-hackathon-submit-gate.ps1 -BaseUrl http://localhost:8000
```

Optional one-command pre-submit audit:

```powershell
scripts/qwencloud-hackathon-audit.ps1 -BaseUrl http://localhost:8000
```

## Step 3 - Alibaba deploy proof (about 1 minute)

- Run deploy preflight:

```powershell
scripts/qwencloud-deploy-preflight.ps1 -BuildImage -SmokeContainer
```

Optional one-command release after credentials and video URL are available:

```powershell
scripts/qwencloud-alibaba-release.ps1 -DemoVideoUrl "https://www.youtube.com/..."
```

- Confirm the final deployed `/health` URL returns the Qwen provider, Track 1,
  model, region, and `deploy/alibaba/serverless-devs.yaml` proof file.
- Capture the required Devpost screenshot from the deployed `/health` proof:

```powershell
scripts/qwencloud-capture-alibaba-proof.ps1 -BaseUrl "https://<function-compute-endpoint>"
```

This writes `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`.

- Render the separate Alibaba backend proof recording:

```powershell
scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl "https://<function-compute-endpoint>"
```

This writes `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4`.

## Step 4 - Demo video (about 1 minute)

- Render the final upload video:

```powershell
scripts/qwencloud-render-demo-video.ps1
```

- Upload `artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`.
- Confirm the public video page plays and remains under 3 minutes.

## Step 5 - Submission packet (about 1 minute)

- Generate the final packet with real URLs:

```powershell
scripts/qwencloud-hackathon-submission-packet.ps1 -RepoUrl "https://github.com/zemeng2015/dream-ai-engineering-copilot" -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>"
```

- Open the generated `artifacts/qwencloud-proof/devpost-submission-packet-*.md`.
- Confirm the packet reports `READY`, including public video URL reachability,
  backend health proof, architecture PNG dimensions, Alibaba screenshot
  readiness, Alibaba proof video readiness, and local demo video under 3 minutes.

## Step 6 - Devpost fill (about 1.5 minutes)

- Title: `DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence`
- Track: `Track 1: MemoryAgent`
- Description: paste from `docs/qwencloud-devpost-form-fields.md`
- Add public repo link
- Add Apache-2.0 link
- Upload `docs/assets/qwencloud-architecture.png`
- Upload `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`
- Upload or link `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4` if
  Devpost requests the separate Alibaba backend recording.
- Add demo video link
- Add deployment proof line and `/health` proof summary text
- Fill the Additional Info fields from `docs/qwencloud-devpost-form-fields.md`
- Add optional blog/social link if published

## Step 7 - Submit

- Click submit on Devpost.
- Immediately open the public project page and confirm links, video, and video
  visibility.

## Emergency fallback if LLM generation fails live

- Keep the video focus on `/health`, memory governance, claim review, and
  traceability.
- Explain network/key instability and continue with governance + audit proof.
- Use `scripts/qwencloud-hackathon-submit-gate.ps1` on your local or deployed
  endpoint to produce one machine-readable proof bundle and a clear pass/fail summary.
