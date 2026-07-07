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
- Devpost submission packet generator that validates final URLs and produces
  copy/paste fields plus judge testing instructions.
- Devpost-friendly architecture PNG upload asset and reproducible export script.
- Alibaba proof integrity gate that validates the capture JSON, screenshot,
  proof recording, and backend URL as one evidence chain.
- Blog/social build journey draft for optional bonus eligibility.
- Focused backend tests and lint for the Qwen integration.

## Must Finish Before Devpost

- Run one live Qwen smoke test with the real `DASHSCOPE_API_KEY`.
- Deploy the container or at least produce a Function Compute dry-run screenshot
  plus `/health` output and the separate Alibaba backend proof recording.
- Upload the rendered sub-3-minute demo video to YouTube, Vimeo, or Youku.
- Generate the final submission packet with public video and deployed backend URLs.
- Upload the architecture PNG into the Devpost submission.
- Publish the optional build journey post if pursuing the blog/social bonus.
- Confirm repository visibility is public and license is Apache-2.0.

## High-Leverage Stretch Work

- Add a Qwen Cloud status chip to the Angular Settings or Trust Center page.
- Add one guided "Hackathon Demo" route that chains memory intake, claim review,
  requirement case, context trail, and audit/eval.
- Add a tiny seeded demo artifact so judges can run the Track 1 flow without
  manually approving claims first.
- Replace placeholders in `docs/qwencloud-build-journey-post.md` with deployed
  backend and video links after publishing.
