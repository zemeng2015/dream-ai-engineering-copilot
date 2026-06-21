<!-- SPDX-License-Identifier: Apache-2.0 -->

# Evaluation Agent

The Evaluation Agent checks whether DREAM outputs are useful, grounded, and
ready for human review. It is deterministic by default and does not require
OpenAI or any paid API.

## What It Evaluates

- Requirement Case analysis
- Impact Map
- Role-specific clarification questions
- Engineering Brief
- Jira Draft
- PR Review Summary
- TestGen report
- General Markdown artifact

## Scorecard

Each evaluation writes a JSON and Markdown scorecard under `artifacts/evals/`.
The scorecard includes:

- overall score
- grade A through F
- pass, warning, or fail status
- dimension scores
- missing critical items
- hallucination warnings
- source coverage
- recommendations

## Dimensions

Requirement-style outputs are scored on completeness, evidence quality, impact
accuracy, role coverage, test awareness, historical context, actionability,
specificity, and hallucination risk.

PR review outputs are scored on changed file awareness, codebase memory usage,
business alignment, test gap detection, operational risk awareness, historical
context, actionability, and hallucination risk.

TestGen reports are scored on target selection quality, validation clarity,
coverage reporting, human review readiness, safety, and actionability.

## Evidence Coverage

The evaluator detects whether an output references:

- domain docs
- architecture docs
- runbooks
- incident docs
- historical Jira
- historical PRs
- testing docs
- concept memory docs
- code files
- test files

## DemoCorp Profiles

DemoCorp eval profiles live in `knowledge_packs/demo_team/eval_profiles/`.
Profiles define expected concepts, code files, tests, docs, incidents, Jira
stories, PRs, roles, and critical risks for common scenarios.

Example:

```bash
dream eval run \
  --target-type engineering_brief \
  --artifact examples/outputs/engineering-brief-async-status-example.md \
  --team demo_team \
  --profile async-status-tracking
```

## API

```bash
curl -X POST http://localhost:8000/eval/run \
  -H "Content-Type: application/json" \
  -d '{"target_type":"engineering_brief","artifact_path":"examples/outputs/engineering-brief-async-status-example.md","team_id":"demo_team","expected_profile":"async-status-tracking"}'
```

Use `GET /eval/runs` and `GET /eval/runs/{evaluation_id}` to inspect stored
scorecards.
