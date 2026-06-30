<!-- SPDX-License-Identifier: Apache-2.0 -->

# Context Intelligence Layer

The Context Intelligence Layer turns a rough engineering request into a
reviewable context package before any workflow generates a brief, ticket draft, PR
review, or test plan. It is the next phase after governed memory distillation:
approved knowledge, codebase memory, evidence graph paths, and promoted intake
documents are assembled into a source-backed context pack.

The layer is not a generic chat surface. It is a deterministic orchestration
boundary that answers:

- what sources were retrieved
- why they were selected
- which claims are approved, candidate, or unknown
- what prompt context will be sent to a model
- how the visible engineering rationale maps back to sources

## Architecture

```text
Request Envelope
  -> Query Planner
  -> Source Retrievers
       -> Knowledge Pack Retriever
       -> Codebase Memory Retriever
       -> Evidence Graph Retriever
       -> Approved Memory Claim Retriever
       -> Promoted Intake Draft Retriever
  -> Context Pack Assembler
  -> Retrieval Trail Recorder
  -> Prompt Preview Builder
  -> Workflow Generator
  -> Standard Logic-Chain Renderer
  -> Retrieval Eval
```

The retrieval boundary should stay small and inspectable. A context pack should
be saved as a JSON artifact and rendered as Markdown or UI cards. Generated
workflow outputs should reference the context pack id instead of re-running
retrieval silently.

## Context Pack Contract

A context pack should contain enough structure for audit, review, prompt
preview, and eval.

```yaml
pack_id: ctx_demo_001
team_id: demo_team
workflow: requirement_case
request:
  text: DemoCorp operators need safer retry guidance for output reconciliation.
  requester_role: BA
  app: ForecastDemo
  component: output-reconciliation
source_refs:
  - source_id: kp_runbook_output_reconciliation
    title: DemoCorp Output Reconciliation Runbook
    status: approved
    source_type: runbook
    path: knowledge_packs/demo_team/docs/imported/output-reconciliation.md
  - source_id: code_OutputCollector
    title: OutputCollector.java
    status: indexed
    source_type: code
retrieval_trail:
  - query: output reconciliation retry partial completion
    retriever: knowledge_pack
    matched_terms: [output, reconciliation, retry]
    rank: 1
    reason: Runbook owns operator recovery steps.
evidence_blocks:
  - claim: Output reconciliation retries must be idempotent.
    source_id: kp_runbook_output_reconciliation
    span: Standard Recovery
    confidence: medium
unknowns:
  - Timeout threshold for marking reconciliation as failed is not defined.
prompt_preview:
  system_policy_summary: Source-backed engineering drafting only.
  context_sections: [relevant_sources, constraints, unknowns]
logic_chain:
  - source: DemoCorp Output Reconciliation Runbook / Standard Recovery
    visible_claim: Retry can be requested only after the run id is stable.
    engineering_implication: API should reject retry requests while execution is running.
    acceptance_check: Retry action is disabled for RUNNING executions.
eval:
  citation_coverage: pending
  approved_only: pending
```

## Retrieval Trail

Every retrieved item should expose:

- retriever name
- source id and source path
- source status: `approved`, `candidate`, `quarantined`, `indexed`, or `unknown`
- query terms or structured filters used
- rank and score
- matched span, heading, symbol, or graph path
- reason for inclusion
- reason for exclusion when a high-similarity source is not eligible

Candidate and quarantined sources can appear in reviewer-only diagnostics, but
they must not be inserted into generation prompts unless a reviewer explicitly
promotes them.

## Prompt Preview

Prompt preview is a review screen and an artifact. It should show the exact
source summaries and constraints that will be sent to the selected provider.
It should not show secrets, private connector credentials, or hidden model
reasoning.

Minimum preview sections:

- task instruction
- source cards with citations
- approved constraints
- open questions
- output schema
- model provider and model name
- excluded source warnings

## Standard Logic-Chain Display

The UI should render a visible engineering rationale, not raw hidden
chain-of-thought. The standard display is:

```text
Source -> Visible Claim -> Engineering Implication -> Acceptance Check
```

Example:

```text
DemoCorp runbook / Standard Recovery
  -> Retry must wait until the execution id is stable.
  -> The retry endpoint needs a status gate.
  -> Disable retry while status is RUNNING and show an operator-facing reason.
```

This format gives leaders and reviewers a traceable decision path without
turning private model reasoning into a product artifact.

## CLI Workflow

The next-phase CLI contract should mirror the current `dream req`, `dream
memory`, and `dream eval` command style.

```bash
dream context pack \
  --team demo_team \
  --workflow requirement_case \
  --request "DemoCorp operators need safer retry guidance for output reconciliation" \
  --role BA \
  --app ForecastDemo \
  --component output-reconciliation

dream context show --pack <pack_id>
dream context prompt-preview --pack <pack_id>
dream context eval --pack <pack_id>
```

`dream req analyze` and later workflow commands should accept `--context-pack
<pack_id>` so the generated output can be tied to a stable retrieval artifact.

## API Workflow

The FastAPI surface should expose the same lifecycle:

```text
POST /context/packs
GET  /context/packs/{pack_id}
GET  /context/packs/{pack_id}/prompt-preview
POST /context/packs/{pack_id}/eval
POST /requirement-cases/{case_id}/analyze?context_pack_id={pack_id}
```

API responses should include artifact paths under the configured artifact root,
not absolute private filesystem paths.

## UI Workflow

The UI should make context review a first-class step:

1. User enters a request and metadata.
2. DREAM builds a context pack.
3. Reviewer inspects the retrieval trail and source cards.
4. Reviewer opens the prompt preview.
5. Reviewer runs retrieval eval.
6. Reviewer approves the context pack for a workflow run.
7. Generated output displays the standard logic-chain view.

The UI should be dense and operational: source tables, status badges, filters,
side-by-side prompt preview, and a compact eval panel. Avoid marketing copy or
decorative explanation inside the application.

## Artifact Isolation

Context packs, prompt previews, retrieval trails, and eval outputs are generated
artifacts. They should be written under the configured artifact root, for
example:

```text
artifacts/context-packs/{team_id}/{pack_id}.json
artifacts/context-packs/{team_id}/{pack_id}.md
artifacts/context-evals/{team_id}/{evaluation_id}.json
```

Private deployments should set `DREAM_ARTIFACT_ROOT` outside the public checkout.
Public demo artifacts must use synthetic DemoCorp inputs only.

## No-Real-Connectors Boundary

The next phase should demo import and context assembly from local files and
synthetic exports only. It should not call real wiki, ticketing, code hosting,
chat, document storage, or email APIs.

Allowed demo sources:

- files under `examples/intake-samples/`
- existing synthetic DemoCorp knowledge packs
- local DemoCorp demo repositories
- generated artifacts under the configured artifact root

## Acceptance Guidance

A next-phase implementation is acceptable when:

- a request can produce a saved context pack with source cards, retrieval trail,
  prompt preview, logic-chain entries, and retrieval eval status
- only approved or indexed sources are inserted into generation prompts
- candidate intake drafts are visible to reviewers but excluded from prompts
- every generated brief or ticket draft links back to the context pack id
- the logic-chain display uses the standard source-to-acceptance format
- artifact paths stay under the configured artifact root
- all demo names remain synthetic DemoCorp names
- no real connector API, private credential, non-demo organization name, or
  company document is required
