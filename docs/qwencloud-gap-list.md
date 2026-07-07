<!-- SPDX-License-Identifier: Apache-2.0 -->

# Qwen Cloud Submission Gap List

## Done In This Branch

- First-class `qwen-cloud` LLM provider.
- API, CLI, config loader, config validator, and provider registry support.
- `/health` exposes provider, model, deployment target, region, and proof file
  without secrets.
- Qwen Cloud example config and `.env.example` entries.
- Alibaba Cloud Function Compute deployment proof.
- Devpost submission brief, architecture doc, architecture SVG, and demo script.
- Final demo video renderer that produces
  `artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`.
- Deploy preflight script that checks env, Serverless Devs, Docker build, and
  local container smoke before Alibaba Cloud push/deploy.
- Focused backend tests and lint for the Qwen integration.

## Must Finish Before Devpost

- Run one live Qwen smoke test with the real `DASHSCOPE_API_KEY`.
- Deploy the container or at least produce a Function Compute dry-run screenshot
  plus `/health` output.
- Upload the rendered sub-3-minute demo video to YouTube/Vimeo/Youku.
- Paste the architecture SVG into the Devpost submission.
- Confirm repository visibility is public and license is Apache-2.0.

## High-Leverage Stretch Work

- Add a Qwen Cloud status chip to the Angular Settings or Trust Center page.
- Add one guided "Hackathon Demo" route that chains memory intake, claim review,
  requirement case, context trail, and audit/eval.
- Add a tiny seeded demo artifact so judges can run the Track 1 flow without
  manually approving claims first.
- Publish a short build-log post for the Devpost blog/social bonus.
