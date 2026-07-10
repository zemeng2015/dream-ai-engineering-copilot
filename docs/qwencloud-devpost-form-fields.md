<!-- SPDX-License-Identifier: Apache-2.0 -->

# Devpost Form Draft (Track 1 MemoryAgent)

This is a copy-ready draft you can paste into Devpost fields.

## Live Devpost draft state

Checked in the signed-in Devpost session on 2026-07-07.

- Draft project: `DREAM Qwen Cloud MemoryAgent`
- Public preview URL: `https://devpost.com/software/dream-qwen-cloud-memoryagent`
- Project details URL: `https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/project_details/edit`
- Additional info URL: `https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/additional-info/edit`
- Finalization URL: `https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/finalization`
- Current status observed: `DRAFT`, `2/5 steps done`
- Browser audit on 2026-07-07 05:15 EDT: Project details required fields
  (`software_description`, `software_tag_list`, first project URL, and
  `software_video_url`) were still empty in the live draft.
- Browser audit on 2026-07-07 05:16 EDT: Additional info fields for submitter
  type, country, new/existing project, start date, Track, repository URL,
  Alibaba proof code URL, architecture upload, deployment screenshot upload,
  AI tools, learning level, and eligibility attestations were still unset in
  the live draft.

Do not click final Submit until the final readiness dashboard reports `READY`.
The eligibility checkboxes are legal attestations and should be confirmed by
Zack at final submission time.

Generate the current structured draft payload with:

```powershell
scripts/qwencloud-devpost-draft-payload.ps1 -AllowDraft
```

This payload is local only. Saving it into Devpost is an external write action
and still requires Zack action-time confirmation.

Generate a local browser-console snippet for safe non-legal text/link fields
with:

```powershell
scripts/qwencloud-devpost-autofill-snippet.ps1 -AllowDraft
```

The snippet does not upload files, check legal attestations, save the draft, or
submit.

Generate the judging alignment scorecard with:

```powershell
scripts/qwencloud-judging-scorecard.ps1 -AllowDraft
```

This scorecard maps the submission to the official judging categories:
Innovation & AI Creativity, Technical Depth & Engineering, Problem Value &
Impact, and Presentation & Documentation.

## Project name

DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence

## Team name

Use your preferred team / handle.

## Description

### Problem

Engineering teams often lose context across tickets, codebases, incidents, and past
reviews. AI assistants then answer from memoryless prompts, which causes hallucination,
inconsistent requirements, and repeated onboarding.

### What we built

DREAM is a source-backed MemoryAgent for engineering workflows. It unifies:

- Qwen-curated cross-session experience (preferences, policies, and reusable lessons)
- Governed remember / supersede / forget / ignore lifecycle decisions
- TTL expiration, explicit forgetting, limited-context recall, and feedback ranking
- Knowledge packs (runbooks, incidents, architecture docs, historical Jira/PR context)
- Codebase memory (files, symbols, concepts, tests, relationships)
- Governed memory claims with human approval/rejection and conflict resolution
- Audit/evaluation/rating feedback to improve future outputs
- Qwen Cloud generation via OpenAI-compatible endpoint

The workflow is traceable and production-minded: generation records include
retrieval and audit metadata, and outputs with retrieved context expose their
source paths for later review.

### Technical stack

- FastAPI + Typer backend with provider abstraction
- OpenAI-compatible Qwen Cloud adapter (`qwen-cloud`)
- Angular workbench and engineering workflow APIs
- SQLite-based audit and eval ledgers
- Docker-tested + Alibaba Cloud Function Compute custom runtime deployment

### Measured Qwen + DREAM evidence

Our primary Track 1 benchmark ran 37 real Qwen curator decisions across 24
synthetic cross-session lifecycle cases. All 24/24 cases passed the lifecycle
contract. Qwen proposal accuracy, governed action accuracy, critical-memory
recall, and token-budget compliance were 100%; forbidden-memory leak was 0%;
the weighted score was 100.0/100. Cases cover durable preference carryover,
conflict supersession, TTL and explicit forgetting, duplicate rejection, and
limited-context recall.

This is a reproducible synthetic benchmark, not a production-effectiveness
claim. The public dataset, runner, methodology, summary, and full report are in
`examples/experience-benchmark/scenarios.yaml`,
`scripts/qwencloud_experience_memory_benchmark.py`, and
`docs/qwen-experience-memory-benchmark.md`.

As a secondary grounding test, a real Qwen Cloud paired run over seven
synthetic engineering cases compared stateless Qwen with Qwen + retrieved DREAM
organization evidence.

The baseline and DREAM conditions used the same `qwen3.7-plus` model, temperature
`0`, output contract, and deterministic reference scorer; the changed variable
was organization evidence absent versus DREAM-retrieved evidence. The mean
deterministic reference score increased from `25.3` to `48.7` (`+23.4`), and
DREAM scored higher in `7/7` paired cases (exact paired permutation
`p=0.0156`). Unsupported references were `0` for the baseline and `0` for
DREAM.

This is a small synthetic benchmark, not a production-effectiveness claim.
Exact retrieval Recall@12 was `35.6%`, which remains a bottleneck, and one
deterministic completion per arm does not estimate sampling variance. Because
latency/token sidecars are incomplete, no latency or token comparison is made.
The machine-readable summary is
`docs/assets/qwen-memory-ab-benchmark-summary.json`; the public methodology and
per-case table are in `docs/qwen-memory-ab-benchmark.md`.

### Why this is Track 1

It is a MemoryAgent: the core value is Qwen-curated experience that persists
across sessions, replaces stale conflicts, forgets at the right time, learns
from feedback, and enters later prompts under a controlled context budget.

### Judging alignment

- Innovation and AI Creativity: Qwen is the semantic memory curator, while
  DREAM adds deterministic lifecycle governance, constrained recall, source
  provenance, and a visible feedback loop.
- Technical Depth and Engineering: DREAM includes provider abstraction,
  API/CLI surfaces, Docker packaging, Alibaba Function Compute deployment,
  architecture assets, CI, release workflow, proof automation, and final
  readiness gates.
- Problem Value and Impact: the product solves a real engineering pain point:
  lost context across Jira, code, incidents, runbooks, and PR history, turning
  it into reusable auditable memory.
- Presentation and Documentation: the repo includes architecture diagrams,
  generated demo/proof videos, deployment proof, field-level Devpost payloads,
  judging scorecard, and a final upload bundle.

## Video link

Render and upload the <3-minute demo video:

```powershell
scripts/qwencloud-render-demo-video.ps1
```

Local upload file:

`artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4`

The video covers:

1) /health proof (Track 1 + qwen-cloud + model + proof file)
2) Memory Hub intake + claim review
3) Requirement case to brief/Jira draft
4) Audit/eval with a human rating action

## Add these links in description or resources section

- Live demo: `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/`
- Judge flow: `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/hackathon-demo`
- Runtime proof: `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/health`
- Showcase: `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/qwencloud/showcase`
- Source code: (public GitHub repository)
- License: Apache-2.0
- Architecture diagram: `docs/assets/qwencloud-architecture.svg`
- Architecture PNG upload asset: `docs/assets/qwencloud-architecture.png`
- Deployment proof: `deploy/alibaba/serverless-devs-runtime.yaml`
- Qwen mode entry: `examples/config/dream.qwen.yaml`
- Optional blog/social draft: `docs/qwencloud-build-journey-post.md`

## Additional info form

These fields were checked against the live Devpost draft for the Qwen Cloud
hackathon.

- Submitter type: `Individual`
- Organization name: leave blank
- Country of residence: `United States`
- Newly built or previously existing project: `New`
- Project start date: `06-21-26`
- If started/existed before May 26: `Not applicable. The public DREAM memory platform release started on 06-21-26; Qwen Cloud Track 1 integration, Alibaba packaging, CI audit, architecture assets, and demo/submission materials were added during the hackathon submission period.`
- Track: `Track 1: MemoryAgent`
- Project link 1: `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/`
- Code repository URL: `https://github.com/zemeng2015/dream-ai-engineering-copilot/tree/codex/champion-memory-loop`
- Alibaba Cloud deployment proof code file: `https://github.com/zemeng2015/dream-ai-engineering-copilot/blob/codex/champion-memory-loop/deploy/alibaba/serverless-devs-runtime.yaml`
- Architecture diagram upload: `docs/assets/qwencloud-architecture.png`
- Alibaba deployment screenshot upload: `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`
  generated with `scripts/qwencloud-capture-alibaba-proof.ps1 -BaseUrl "<deployed-backend-url>"`
- Alibaba backend proof recording: `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4`
  generated with `scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl "<deployed-backend-url>"`
- Blog/social journey URL: optional; use a published copy of `docs/qwencloud-build-journey-post.md` if available
- AI tools leveraged: `Qwen Cloud for the runtime LLM provider, OpenAI Codex for implementation assistance, GitHub Actions for CI verification, and local automation scripts for audit, render, deploy preflight, and submission packet generation.`
- Learning level: `Significant`

### Live field IDs

Use these IDs only as a sanity check when filling the live form; Devpost may
change them after a form refresh.

| Devpost field | Observed element ID |
|---|---|
| Project story | `software_description` |
| Built with | `software_tag_list` |
| Project link 1 | `software_urls_attributes_0_url` |
| Video demo link | `software_video_url` |
| Submitter type | `participants_submission_requirements_submission_field_values_attributes_0_value` |
| Country of residence | `participants_submission_requirements_submission_field_values_attributes_2_values` |
| New/existing project | `participants_submission_requirements_submission_field_values_attributes_3_value` |
| Project start date | `participants_submission_requirements_submission_field_values_attributes_4_value` |
| Pre-existing project explanation | `participants_submission_requirements_submission_field_values_attributes_5_value` |
| Track | `participants_submission_requirements_submission_field_values_attributes_6_value` |
| Code repository URL | `participants_submission_requirements_submission_field_values_attributes_7_value` |
| Alibaba deployment proof code URL | `participants_submission_requirements_submission_field_values_attributes_8_value` |
| Architecture diagram upload | `submission_field_file_27544_add_files` |
| Alibaba deployment screenshot upload | `submission_field_file_27832_add_files` |
| Optional blog/social URL | `participants_submission_requirements_submission_field_values_attributes_11_value` |
| AI tools leveraged | `participants_submission_requirements_submission_field_values_attributes_12_value` |
| Learning level | `participants_submission_requirements_submission_field_values_attributes_13_value` |
| Age of majority attestation | `participants_submission_requirements_submission_field_values_attributes_14_value` |
| Eligible jurisdiction attestation | `participants_submission_requirements_submission_field_values_attributes_15_value` |
| Not sponsor/government employee attestation | `participants_submission_requirements_submission_field_values_attributes_16_value` |
| Final Official Rules / Terms of Service attestation | finalization page checkbox |

### Current live blockers

- Project details and Additional info still need to be pasted into the live
  Devpost draft and saved. Saving the draft is an external write action and
  should only be done after Zack confirms it at action time.
- `software_video_url` is empty until the demo MP4 is uploaded to YouTube,
  Vimeo, Facebook Video, or Youku. YouTube or Vimeo are the least ambiguous
  final choices because the public overview and Official Rules list slightly
  different accepted platform sets.
- `software_urls_attributes_0_url` is ready:
  `https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/`. The repository
  URL belongs in the required additional-info repository field.
- `submission_field_file_27544_add_files` needs
  `docs/assets/qwencloud-architecture.png`.
- `submission_field_file_27832_add_files` is ready at
  `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`, generated from
  the real Alibaba Cloud backend.
- The separate Alibaba backend recording is ready at
  `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4` for the proof bundle.
- Browser file upload automation requires Chrome extension file access. If a
  file chooser reports `Not allowed`, open `chrome://extensions`, click Details
  under the Codex extension, and enable `Allow access to file URLs`.
- Legal eligibility checkboxes must be confirmed by Zack before final submit.
- Finalization also requires Zack to confirm the Official Rules and Devpost
  Terms of Service checkbox before pressing `Submit project`.

## Notes

- Keep secrets off every public field.
- Mention `DREAM with qwen-cloud`, `Track 1 MemoryAgent`, and `Alibaba Cloud Function Compute` in description.
- If live Qwen endpoints are temporarily unstable, include fallback plan in demo narrative
  while still showing governance, memory scan, and `/health` verification.
