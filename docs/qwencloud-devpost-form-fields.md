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

- Knowledge packs (runbooks, incidents, architecture docs, historical Jira/PR context)
- Codebase memory (files, symbols, concepts, tests, relationships)
- Governed memory claims with human approval/rejection and conflict resolution
- Audit/evaluation/rating feedback to improve future outputs
- Qwen Cloud generation via OpenAI-compatible endpoint

The workflow is traceable and production-minded: every generated answer is tied to
retrieved evidence and can be audited later.

### Technical stack

- FastAPI + Typer backend with provider abstraction
- OpenAI-compatible Qwen Cloud adapter (`qwen-cloud`)
- Angular workbench and engineering workflow APIs
- SQLite-based audit and eval ledgers
- Docker + Alibaba Cloud Function Compute custom container deployment

### Why this is Track 1

It is a MemoryAgent: the core value is durable, reviewable memory that improves
decision quality across requirement drafting, PR review, and engineering workflows.

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

- Source code: (public GitHub repository)
- License: Apache-2.0
- Architecture diagram: `docs/assets/qwencloud-architecture.svg`
- Architecture PNG upload asset: `docs/assets/qwencloud-architecture.png`
- Deployment proof: `deploy/alibaba/serverless-devs.yaml`
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
- Code repository URL: `https://github.com/zemeng2015/dream-ai-engineering-copilot`
- Alibaba Cloud deployment proof code file: `https://github.com/zemeng2015/dream-ai-engineering-copilot/blob/main/deploy/alibaba/serverless-devs.yaml`
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
  Vimeo, or Youku.
- `submission_field_file_27544_add_files` needs
  `docs/assets/qwencloud-architecture.png`.
- `submission_field_file_27832_add_files` needs
  `artifacts/qwencloud-proof/alibaba-deployment-screenshot.png`, generated
  from the real Alibaba Cloud backend.
- The separate Alibaba backend recording must also exist at
  `artifacts/qwencloud-proof/alibaba-deployment-proof.mp4` and be available
  for the proof bundle.
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
