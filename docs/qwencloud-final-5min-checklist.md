# SPDX-License-Identifier: Apache-2.0

# Final 5-minute Checklist Before Devpost Submit

## Step 1 — Runtime proof (about 1 minute)

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

- Confirm output includes:
  - `llm_provider: qwen-cloud`
  - `track: Track 1: MemoryAgent`
  - `proof_file: deploy/alibaba/serverless-devs.yaml`

## Step 2 — Artifact evidence (about 1 minute)

- Confirm these are in repo:
  - `docs/qwencloud-submission.md`
  - `docs/qwencloud-architecture.md`
  - `docs/assets/qwencloud-architecture.svg`
  - `docs/qwencloud-demo-video-script.md`
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

## Step 3 — Devpost fill (about 1.5 minutes)

- Title: `DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence`
- Track: `Track 1: MemoryAgent`
- Description: paste from `docs/qwencloud-devpost-form-fields.md`
- Add public repo link
- Add Apache-2.0 link
- Upload architecture image
- Add demo video link
- Add deployment proof line and `/health` proof summary text

## Step 4 — Submit

- Click submit on Devpost.
- Immediately open the public project page and confirm links, video, and video
  visibility.

## Emergency fallback if LLM generation fails live

- Keep the video focus on `/health`, memory governance, claim review, and
  traceability.
- Explain network/key instability and continue with governance + audit proof.
Use `scripts/qwencloud-hackathon-submit-gate.ps1` on your local or deployed
endpoint to produce one machine-readable proof bundle and a clear pass/fail summary.
