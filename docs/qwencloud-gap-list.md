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
- Guided Angular `/hackathon-demo` route that links the judge flow, Qwen proof
  signals, local proof commands, and remaining Devpost gates.
- Live Angular `/health` proof panel on `/hackathon-demo` that reads provider,
  model, deployment target, region, API-key status, and proof file from the
  running backend with an offline-safe fallback.
- Seeded judge demo artifact generator,
  `scripts/qwencloud_seed_demo_artifact.py`, that creates a portable artifact
  root with latest memory scan, approved review ledger, context card, and ZIP.
- Judge rehearsal dashboard, `scripts/qwencloud-judge-rehearsal.ps1`, that
  refreshes seeded memory, local runtime proof, frontend build proof, judging
  scorecard, and final readiness into a single demo-shot report.
- Final external handoff pack, `scripts/qwencloud-final-external-handoff.ps1`,
  that packages the action-time order, safety boundaries, generated reports,
  and copy/paste commands for real video upload, Alibaba secrets/deploy,
  Devpost field save, legal submit, and post-submit verification.
- Focused backend tests and lint for the Qwen integration.

## Must Finish Before Devpost

- Run one live Qwen smoke test with the real `DASHSCOPE_API_KEY`.
- Deploy the container or at least produce a Function Compute dry-run screenshot
  plus `/health` output and the separate Alibaba backend proof recording.
- Upload the rendered sub-3-minute demo video to YouTube, Vimeo, or Facebook Video.
- Generate the final submission packet with public video and deployed backend URLs.
- Upload the architecture PNG into the Devpost submission.
- Publish the optional build journey post if pursuing the blog/social bonus.
- Confirm repository visibility is public and license is Apache-2.0.

## High-Leverage Stretch Work

- Replace placeholders in `docs/qwencloud-build-journey-post.md` with deployed
  backend and video links after publishing.
