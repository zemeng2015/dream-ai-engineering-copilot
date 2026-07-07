<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Contest Launch Checklist

## Before final day

- [ ] Git branch clean and pushed (`main`).
- [ ] Public repo url ready.
- [ ] `LICENSE` visible as Apache-2.0.
- [ ] Qwen config file present: `examples/config/dream.qwen.yaml`.
- [ ] Architecture PNG ready: `docs/assets/qwencloud-architecture.png`.
- [ ] Alibaba deployment screenshot path reserved: `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`.
- [ ] Alibaba deployment proof recording path reserved: `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4`.
- [ ] One-command release script present: `scripts/qwencloud-alibaba-release.ps1`.
- [ ] One-command local proof script present: `scripts/qwencloud-run-local-proof.ps1`.
- [ ] Health endpoint smoke works and returns `llm_provider: qwen-cloud`.

## Runbook (submission window)

1. Set env and launch API:

```powershell
$env:DREAM_CONFIG_FILE="examples/config/dream.qwen.yaml"
$env:DASHSCOPE_API_KEY="<key>"
uvicorn dream.api.app:app --reload --host 0.0.0.0 --port 8000
```

2. Run health proof:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
```

3. Run one Qwen generation proof:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/requirements/draft `
  -Body '{"team_id":"demo_team","rough_business_request":"Users need to know why a forecast job is stuck running","llm_provider":"qwen-cloud"}' `
  -ContentType "application/json"
```

4. Validate artifact files:
- `docs/qwencloud-submission.md`
- `docs/qwencloud-architecture.md`
- `docs/assets/qwencloud-architecture.svg`
- `docs/assets/qwencloud-architecture.png`
- `docs/qwencloud-demo-video-script.md`
- `docs/qwencloud-build-journey-post.md`
- `deploy/alibaba/serverless-devs.yaml`
- `deploy/alibaba/README.md`
- `docs/qwencloud-devpost-form-fields.md`
- `docs/qwencloud-final-5min-checklist.md`

5. Deploy proof:
- Run preflight:
  ```powershell
  scripts/qwencloud-deploy-preflight.ps1 -BuildImage -SmokeContainer
  ```
- Or run the full release script after video URL is available:
  ```powershell
  scripts/qwencloud-alibaba-release.ps1 -DemoVideoUrl "<public-video-url>"
  ```
- Build and push image to `$env:ALIBABA_CLOUD_CONTAINER_IMAGE`.
- Run Serverless Devs deployment using `deploy/alibaba/serverless-devs.yaml`.
- Re-test deployed URL `.../health`.
- Capture Devpost proof screenshot:
  ```powershell
  scripts/qwencloud-capture-alibaba-proof.ps1 -BaseUrl <deployed-url>
  ```
- Render the separate Alibaba backend proof recording:
  ```powershell
  scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl <deployed-url>
  ```

6. Save reproducible proof bundle:

```powershell
scripts/qwencloud-hackathon-proof.ps1 -BaseUrl <deployed-url>
```

For local proof before deploy, run:

```powershell
scripts/qwencloud-run-local-proof.ps1
```

Optional strict gate (health + draft + field checks):

```powershell
scripts/qwencloud-hackathon-submit-gate.ps1 -BaseUrl <deployed-url>
```

Optional full audit report (includes file + repo + remote visibility checks):

```powershell
scripts/qwencloud-hackathon-audit.ps1 -BaseUrl <deployed-url>
```

7. Record or render demo with <3 minute duration.

8. Generate final Devpost packet:

```powershell
scripts/qwencloud-hackathon-submission-packet.ps1 -RepoUrl "https://github.com/zemeng2015/dream-ai-engineering-copilot" -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-url>"
```

The packet must report `READY`; failures on the public video URL, deployed
backend URL, Alibaba screenshot, Alibaba proof video, or upload asset checks
mean the Devpost submission is still not complete.

9. Run final readiness:

```powershell
scripts/qwencloud-final-readiness.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-url>"
```

This must report `READY` before the Devpost form is submitted.

10. Create final upload bundle:

```powershell
scripts/qwencloud-final-upload-bundle.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-url>"
```

## Submission packet

- GitHub link
- Apache 2.0 link
- Architecture image
- Alibaba deployment screenshot
- Alibaba backend proof recording
- Demo video link
- Proof files / deployment proof
- 1-2 sentence demo result summary from live run

```text
Submission done checklist item can only be marked complete after external Devpost
submission confirms all required fields are accepted.
```
