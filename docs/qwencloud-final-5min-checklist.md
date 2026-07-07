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
  - `docs/qwencloud-demo-video-captions.srt`
  - `docs/qwencloud-demo-video-transcript.md`
  - `docs/qwencloud-video-upload-handoff.md`
  - `docs/qwencloud-build-journey-post.md`
  - `deploy/alibaba/serverless-devs.yaml`
  - `deploy/alibaba/README.md`
  - `docs/qwencloud-devpost-form-fields.md`
  - `frontend/src/app/features/hackathon-demo/hackathon-demo.component.ts`
  - `scripts/qwencloud_seed_demo_artifact.py`
  - `scripts/qwencloud-judge-rehearsal.ps1`
  - `scripts/qwencloud-final-external-handoff.ps1`
  - `scripts/qwencloud-official-source-refresh.ps1`
  - `scripts/qwencloud-deadline-guard.ps1`
  - `scripts/qwencloud-live-inputs-intake.ps1`
  - `scripts/qwencloud-github-ci-proof.ps1`

- Open the judge-facing Angular route:
  `http://localhost:4300/hackathon-demo`

- Generate the seeded judge demo artifact if you want approved memory available
  immediately during the live walkthrough:

```powershell
python scripts/qwencloud_seed_demo_artifact.py --promote-count 6
```

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

Optional judge rehearsal dashboard before recording or presenting:

```powershell
scripts/qwencloud-judge-rehearsal.ps1 -AllowDraft
```

## Step 3 - Alibaba deploy proof (about 1 minute)

- Run deploy preflight:

```powershell
Copy-Item .env.qwencloud.local.example .env.qwencloud.local
# Fill .env.qwencloud.local locally. It is ignored by git.
scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft
scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft
scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer -AllowDraft
```

Optional one-command release after credentials and video URL are available:

```powershell
scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..."
```

One-command final sprint dashboard before doing any external action:

```powershell
scripts/qwencloud-final-sprint.ps1 -EnvFile .env.qwencloud.local -AllowDraft
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

- Validate the Alibaba proof evidence chain:

```powershell
scripts/qwencloud-validate-alibaba-proof.ps1 -BackendUrl "https://<function-compute-endpoint>"
```

## Step 4 - Demo video (about 1 minute)

- Render the final upload video:

```powershell
scripts/qwencloud-render-demo-video.ps1
scripts/qwencloud-video-publication-handoff.ps1
```

- Upload `artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`.
- Use `docs/qwencloud-video-upload-handoff.md` and the latest
  `video-publication-handoff-*.md` for the title, description, MP4 hash,
  thumbnail hash, caption hash, platform rules, and Chrome upload troubleshooting.
- If Codex-controlled Chrome reports `Not allowed` on file upload, open
  `chrome://extensions`, click Details under the Codex extension, and enable
  `Allow access to file URLs`.
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
- Run the final readiness dashboard and confirm it reports `READY`:

```powershell
scripts/qwencloud-official-source-refresh.ps1
scripts/qwencloud-deadline-guard.ps1
scripts/qwencloud-live-inputs-intake.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>"
scripts/qwencloud-github-ci-proof.ps1
scripts/qwencloud-final-readiness.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>"
```

- Or run the final one-command gate:

```powershell
scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>" -RefreshAlibabaProof
```

This command refreshes the official Devpost overview/rules source before it
checks video status, Alibaba proof, packet readiness, and the upload bundle.

- Create the final upload bundle:

```powershell
scripts/qwencloud-final-upload-bundle.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>"
```

- Generate the final action board if any signal is still DRAFT:

```powershell
scripts/qwencloud-final-action-board.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>" -AllowDraft
```

- Or run the final sprint dashboard, which refreshes video status, cloud
  credentials, live inputs, judging scorecard, GitHub secrets, release plan,
  final packet, upload bundle, and final action board in one pass:

```powershell
scripts/qwencloud-final-sprint.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>" -RefreshAlibabaProof -AllowDraft
```

- Open the generated `devpost-handoff-*.html` from the upload bundle and use it
  as the final copy/paste dashboard while filling Devpost.
- Generate the final external handoff pack before touching real accounts,
  uploads, deployment, or legal submit:

```powershell
scripts/qwencloud-final-external-handoff.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "https://www.youtube.com/..." -BackendUrl "https://<function-compute-endpoint>" -AllowDraft
```

- Confirm the bundle also includes the latest `deploy-preflight-*.md/json` so
  the Docker build and container `/health` smoke proof is available with the
  upload files.
- If deploying through GitHub Actions, confirm
  `scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft` reports all
  required secrets present before running `Qwen Cloud Release`.

## Step 6 - Devpost fill (about 1.5 minutes)

- Use the existing live draft:
  `https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/project_details/edit`
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
- Before uploading files through Codex-controlled Chrome, ensure the Codex
  Chrome extension has `Allow access to file URLs` enabled.
- Zack must personally confirm the age, jurisdiction, and sponsor/government
  employment eligibility checkboxes before final submit.
- Zack must personally confirm the final Official Rules / Devpost Terms of
  Service checkbox on the finalization page before pressing `Submit project`.

## Step 7 - Submit

- Click submit on Devpost.
- Immediately open the public project page and confirm links, video, and video
  visibility.
- Save final completion evidence:

```powershell
scripts/qwencloud-post-submit-verification.ps1 -DevpostProjectUrl "https://devpost.com/software/<project-slug>" -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"
```

## Emergency fallback if LLM generation fails live

- Keep the video focus on `/health`, memory governance, claim review, and
  traceability.
- Explain network/key instability and continue with governance + audit proof.
- Use `scripts/qwencloud-hackathon-submit-gate.ps1` on your local or deployed
  endpoint to produce one machine-readable proof bundle and a clear pass/fail summary.
