<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenAI Build Week Submission Kit

## Project

**DREAM Engineering Change Loop**

Track: **Developer Tools**

Tagline: Turn one rough engineering request into an evidence-backed Jira draft,
PR review, isolated JUnit tests, and an auditable quality score.

## Devpost description

Engineering assistants usually optimize one step while losing the context that
connects the entire change. DREAM treats organizational and codebase context as
governed memory, then carries that evidence through a complete change loop.

A developer enters a rough request. DREAM distills source-backed memory and an
evidence graph, creates a Jira-ready draft with explicit open questions, reviews
a PR diff against that intent, asks GPT-5.6 to generate validated JUnit 5 test
candidates through JTestGen, and evaluates every artifact. The workflow exposes
its sources, model provenance, warnings, scores, and artifact paths instead of
presenting an opaque answer.

Codex was the development environment for the Build Week integration. GPT-5.6
is a meaningful runtime component through the native Responses API: it powers
requirement synthesis, PR reasoning, structured test generation, and an
optional judging layer. Deterministic checks remain active so the model never
becomes the sole quality gate.

The result is a developer tool with practical safety boundaries: Jira remains a
draft, review remains advisory, generated tests stay outside the repository,
and all consequential actions require a human.

## What was built during Build Week

- Native GPT-5.6 Responses API provider with model and reasoning provenance.
- Unified five-stage `EngineeringLoopService` and FastAPI endpoint.
- Real JTestGen adapter for structured, validated, isolated JUnit 5 candidates.
- Deterministic and optional GPT-5.6 evaluation across Jira, review, and tests.
- Responsive Angular control room with live and credential-free demo modes.
- Integration tests, safety validation, audit artifacts, and submission docs.

Build Week implementation branch: `codex/openai-build-week`  
Pre-build baseline: `d3f8a9f`  
Primary implementation commit: `353e0fa`  
Review range: `d3f8a9f..codex/openai-build-week`

Before submitting, add the Codex `/feedback` Session ID below. Do not claim
pre-existing DREAM features as newly built; judge the new integration and files
in the review range above.

Codex Session ID: **PENDING — run `/feedback` in the build thread**

## Three-minute video script

**0:00-0:20 — Problem.** Show a rough change request. Explain that requirements,
review, tests, and evaluation normally lose context between tools.

**0:20-0:40 — Architecture.** Show the five-stage rail and say that governed
memory carries evidence through the full engineering loop.

**0:40-1:35 — Live run.** Enable Live GPT-5.6, run the workflow, and narrate the
stage transitions: memory, Jira draft, PR review, JTestGen, eval.

**1:35-2:15 — Evidence.** Open the result summary, Jira artifact, PR review, and
an isolated generated JUnit candidate. Point out source paths, provider/model
provenance, warnings, and the overall score.

**2:15-2:40 — Safety.** Emphasize that the app does not post Jira, comment on a
PR, run generated code, or write tests into the repository without a human.

**2:40-3:00 — Build Week.** Show the repository's Build Week commit range and
README, state that Codex built the integration and GPT-5.6 powers the runtime,
then finish on the completed five-stage result.

## Final submission checklist

- [ ] Public repository URL points to the Build Week branch or merged commit.
- [ ] README identifies Codex and GPT-5.6 usage and includes a reproducible path.
- [ ] Post-July-13 commit range is recorded here.
- [ ] Run `/feedback` in the Codex thread and paste its Session ID here.
- [ ] Public YouTube video is no longer than three minutes and contains audio.
- [ ] Video demonstrates a real live GPT-5.6 run and visible output artifacts.
- [ ] Devpost fields, team details, country eligibility, and rules are rechecked.
- [ ] Submission is completed before the published deadline.
