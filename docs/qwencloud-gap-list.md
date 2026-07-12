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
- Judging evidence matrix, `docs/qwencloud-judging-evidence-matrix.md`, that
  maps each official scoring area to static repo evidence and the live external
  proof still required before final submit.
- Final external handoff pack, `scripts/qwencloud-final-external-handoff.ps1`,
  that packages the action-time order, safety boundaries, generated reports,
  and copy/paste commands for real video upload, Alibaba secrets/deploy,
  Devpost field save, legal submit, and post-submit verification.
- Official source refresh report, `scripts/qwencloud-official-source-refresh.ps1`,
  that re-checks the public Devpost overview/rules pages and records current
  deadline, Track 1, submission evidence, judging weights, and accepted video
  platform wording before final submit.
- Focused backend tests and lint for the Qwen integration.
- Submitted Devpost entry with all five steps complete, including the Alibaba
  Workbench screenshot, architecture upload, deployment code URL, Track 1,
  testing instructions, eligibility declarations, and public build-journey URL.
- Public Alibaba Function Compute Judge Arena using `qwen3.7-plus`, with live
  health/showcase proof and a real remember/supersede/recall flow.
- Reproducible 7-case paired benchmark and 24-case lifecycle benchmark with
  public methodology, limitations, Qwen request receipts, and stability data.
- Full founder-led V2 video pipeline using real browser capture and Alibaba
  Model Studio `qwen3-tts-vc-2026-01-22` narration. The local 146.73-second
  candidate passes codec, duration, loudness, black-frame, evidence, and hash
  validation.
- Four local 1800x1200 Devpost gallery candidates covering positioning, live
  proof, measured impact, and deployed architecture.
- Durable Alibaba Cloud Tablestore repository using a Singapore CU-mode,
  high-performance ZRS instance, zero reserved throughput, scoped RAM role,
  and partition-local transactions.
- Real-cloud 20-request contention proof: 20 successful writes, 20 decision
  receipts, 19 superseded memories, and exactly one active truth.
- Frozen Function Compute runtime `cb6255b7a1565a631daec6215bd146f495d97df8`
  with Tablestore, temporary role credentials, matching concurrency caps of 20,
  and exact build/instance evidence in `/health` and response headers.
- Public HTTP contention proof: 20/20 successful requests, no 429 responses,
  one active truth, 19 superseded histories, and 20 decision receipts in 7.494
  seconds.
- Real `qwen3.7-plus` memory persisted across two different FC instance IDs,
  including the same memory ID, decision ID, request/response hashes, and Qwen
  provider request ID after redeployment.

## Must Finish Before Final Submission

- Obtain user approval for the full V2 candidate, upload the approved cut to
  YouTube, replace the Devpost video, and verify the embedded public result.
- Upload the four approved public gallery images to Devpost.
- Remove evidence drift by making the deployment metadata, live showcase,
  repository docs, final bundle, and Devpost all reference the same current
  video URL and source commit.
- Add a human-reviewed evaluation slice beside the synthetic deterministic
  benchmarks. Keep `+23.4`, `24/24`, and `100.0/100` explicitly scoped to their
  published synthetic benchmark contracts.
- Produce the concise sponsor-facing presentation deck referenced by the Qwen
  event page, even though it is not an explicit Official Rules requirement.
- Require a current strict final-bundle manifest during post-submit verification.

## Current Integrity Boundaries

- The public Function Compute runtime is frozen at `cb6255b7a156...`. Any
  runtime or deployment-config change invalidates the committed build and
  instance proof and must be followed by the full seed/redeploy/verify flow.
- The legacy audit ledger and disposable generated artifacts still use `/tmp`;
  experience memory and decision receipts use durable Tablestore transactions.
- The paired and lifecycle benchmarks use synthetic engineering scenarios. They
  demonstrate reproducible lifecycle behavior, not production effectiveness.
- The default `fcapp.run` endpoint is a public Function Compute test domain, not
  a custom production domain.
- Current Devpost status is `Submitted` with 5/5 steps complete. The official
  code-freeze deadline is July 20, 2026 at 2:00pm PDT; judging ends August 11,
  so the free demo and evidence URLs must remain available through that date.
