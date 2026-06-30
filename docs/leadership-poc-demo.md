<!-- SPDX-License-Identifier: Apache-2.0 -->

# Leadership POC Demo

This script shows the next DREAM phase: ingest synthetic DemoCorp knowledge,
review it, promote it, build a context pack, preview the prompt, generate a
source-backed planning artifact, and verify the retrieval trail.

Target duration: 12 to 15 minutes.

## Demo Setup

- Use only synthetic DemoCorp data.
- Use local files under `examples/intake-samples/`.
- Use a local artifact root.
- Do not connect to real ticketing, wiki, code hosting, chat, document storage,
  or email systems.
- Keep the story on ForecastDemo and DemoCorp Forecast Platform.

Suggested request:

```text
DemoCorp operators need a safer way to retry output reconciliation after a
forecast job partially completes. They want guidance in the UI, a status gate,
and test coverage for duplicate retry prevention.
```

## Story Flow

### 1. Open With The Problem

Talk track:

```text
DemoCorp has useful engineering knowledge, but it lives in runbooks, HLDs, and
policy documents. DREAM turns that material into reviewed memory before an AI
workflow uses it.
```

Show:

- `examples/intake-samples/runbook-output-reconciliation.md`
- `examples/intake-samples/confluence-hld-forecast-orchestration-export.md`
- `examples/intake-samples/docx-placeholder/README.md`

### 2. Import Synthetic Knowledge

Show the intended CLI or UI import path:

```bash
dream intake import \
  --team demo_team \
  --source examples/intake-samples/runbook-output-reconciliation.md \
  --source-type runbook \
  --app ForecastDemo \
  --component output-reconciliation

dream intake import \
  --team demo_team \
  --source examples/intake-samples/confluence-hld-forecast-orchestration-export.md \
  --source-type confluence_export \
  --app ForecastDemo \
  --component forecast-orchestration
```

Expected result:

- two pending structured knowledge drafts
- detected titles, components, headings, and candidate claims
- source spans visible next to each candidate claim

### 3. Show The Review Queue

Talk track:

```text
DREAM does not treat uploads as trusted memory. The reviewer can approve,
reject, quarantine, or edit metadata before promotion.
```

Checklist:

- approve the runbook draft
- approve the HLD draft
- leave the DOCX placeholder as parser-boundary documentation
- record reviewer and reason
- show that candidate claims have citations

### 4. Promote Reviewed Drafts

Show:

```bash
dream intake promote --draft <runbook_draft_id> --target knowledge-pack
dream intake promote --draft <hld_draft_id> --target knowledge-pack
dream kb search --team demo_team --query "output reconciliation retry"
```

Expected result:

- promoted documents become searchable
- draft and promotion artifacts remain under the artifact root
- rejected or unparsed files do not appear in retrieval

### 5. Build The Context Pack

Show:

```bash
dream context pack \
  --team demo_team \
  --workflow requirement_case \
  --request "DemoCorp operators need a safer way to retry output reconciliation after a forecast job partially completes." \
  --role BA \
  --app ForecastDemo \
  --component output-reconciliation
```

Expected result:

- context pack id
- source cards
- retrieval trail
- unknowns
- prompt preview
- retrieval eval status

### 6. Inspect Retrieval Trail

Required story beat:

```text
The runbook is retrieved because it owns operator recovery. The HLD is retrieved
because it defines the orchestration components. Codebase memory is retrieved
because retry idempotency maps to OutputCollector and execution status handling.
```

Show at least three source cards:

- DemoCorp Output Reconciliation Runbook
- DemoCorp Forecast Orchestration HLD
- DemoCorp codebase memory for output collection or execution status

### 7. Preview The Prompt

Talk track:

```text
Before generation, reviewers can see the exact source summaries, constraints,
unknowns, and output schema. Candidate or quarantined drafts are excluded.
```

Checklist:

- source cards have citations
- open questions are visible
- model/provider selection is visible
- no raw secrets or private connector settings appear

### 8. Generate The Planning Artifact

Use the stable context pack with the existing Requirement Case style workflow:

```bash
dream req create \
  --team demo_team \
  --request "DemoCorp operators need a safer way to retry output reconciliation after a forecast job partially completes." \
  --role BA \
  --app ForecastDemo \
  --component output-reconciliation

dream req analyze --case <case_id>
dream req brief --case <case_id>
dream req jira --case <case_id>
```

Expected result:

- impact map references operator UI, status gate, backend idempotency, and tests
- engineering brief cites the promoted runbook and HLD
- ticket draft includes acceptance criteria and open questions

### 9. Show Standard Logic Chain

Display the visible rationale in the standard format:

```text
DemoCorp runbook / Standard Recovery
  -> Retry must wait until execution status is stable.
  -> Backend should reject retry while status is RUNNING.
  -> Acceptance: retry action is disabled for RUNNING executions.

DemoCorp HLD / Component Responsibilities
  -> OutputCollector owns result materialization.
  -> Duplicate retry prevention belongs near output collection.
  -> Acceptance: repeated retry request returns an idempotent response.
```

This is the source-backed engineering rationale, not hidden model reasoning.

### 10. Run Retrieval Eval And Close

Show:

```bash
dream context eval --pack <pack_id>
dream eval run \
  --target-type engineering_brief \
  --case <case_id> \
  --team demo_team
```

Leadership close:

```text
The value is not just generation. DREAM shows how company knowledge becomes
reviewed memory, how each answer is grounded, and how leaders can inspect the
trail before the result enters delivery work.
```

## Acceptance Checklist

The POC passes when:

- all visible names are synthetic DemoCorp names
- sample runbook and HLD import into pending drafts
- DOCX placeholder clearly shows the parser boundary
- human review happens before promotion
- promoted drafts are searchable
- context pack shows retrieval trail, source cards, prompt preview, unknowns,
  and eval status
- logic chain uses `Source -> Visible Claim -> Engineering Implication ->
  Acceptance Check`
- generated brief or ticket draft cites the context pack or promoted sources
- artifact paths remain under the configured artifact root
- no real connector, non-demo data, or private secret is required

## Common Demo Risks

- Do not call the Confluence sample a live connector.
- Do not imply DOCX parsing is complete until a parser is implemented.
- Do not show candidate drafts as trusted generation context.
- Do not use non-demo organization names, URLs, tickets, PRs, logs, or screenshots.
- Do not skip the review step; it is the trust story.
