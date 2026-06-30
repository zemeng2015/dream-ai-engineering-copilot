<!-- SPDX-License-Identifier: Apache-2.0 -->

# Knowledge Intake Pipeline

The Knowledge Intake Pipeline turns uploaded or imported engineering documents
into structured knowledge drafts. Human reviewers decide what becomes durable
DREAM memory. This keeps the system useful for real teams without letting raw
uploads silently become trusted context.

The phase focuses on local synthetic files:

- a DemoCorp runbook Markdown file
- a DemoCorp Confluence-style HLD export
- a DOCX placeholder/readme that documents the expected future upload path

No real enterprise connector is required for the POC.

## Architecture

```text
Local Upload / File Import
  -> Source Registry
  -> Format Normalizer
  -> Segmenter
  -> Metadata Extractor
  -> Structured Knowledge Draft
  -> Validation Gates
  -> Review Queue
  -> Promotion Writer
  -> Retrieval Refresh
  -> Retrieval Eval
```

The pipeline should treat every imported file as evidence, not authority.
Imported content becomes a candidate draft with source spans, proposed metadata,
and validation warnings. Promotion is a separate human action.

## Source Types

| Source type | POC input | Normalization |
| --- | --- | --- |
| Runbook | `examples/intake-samples/runbook-output-reconciliation.md` | Markdown with front matter and headings |
| Confluence HLD export | `examples/intake-samples/confluence-hld-forecast-orchestration-export.md` | Markdown plus HTML-like blocks |
| DOCX | `examples/intake-samples/docx-placeholder/README.md` | Placeholder until a parser is wired in |

The Confluence sample is an exported file, not a live Confluence connector. The
DOCX placeholder documents the expected behavior without committing binary test
data.

## Draft Contract

A structured knowledge draft should be stored as JSON and rendered in the UI.

```yaml
draft_id: kid_demo_001
team_id: demo_team
source_record:
  source_type: runbook
  original_name: runbook-output-reconciliation.md
  import_method: local_file
  synthetic: true
  source_hash: sha256:demo
proposed_document:
  title: DemoCorp Output Reconciliation Runbook
  app: ForecastDemo
  component: output-reconciliation
  doc_type: runbook
  target_path: knowledge_packs/demo_team/docs/imported/output-reconciliation.md
source_spans:
  - span_id: span_standard_recovery
    heading: Standard Recovery
    preview: Verify the run id, confirm status is not RUNNING, request retry.
candidate_claims:
  - text: Output reconciliation retry should be blocked while execution is RUNNING.
    support: span_standard_recovery
    status: candidate
validation:
  citation_valid: true
  secret_like_content: false
  real_connector_required: false
  warnings: []
review:
  status: pending
  reviewer: null
  reason: null
```

## CLI Workflow

The next-phase CLI should use explicit import, review, and promotion verbs.

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

dream intake list --team demo_team --status pending
dream intake show --draft <draft_id>

dream intake review \
  --draft <draft_id> \
  --status approved \
  --reviewer demo.lead \
  --reason "Synthetic runbook matches DemoCorp recovery policy."

dream intake promote --draft <draft_id> --target knowledge-pack
dream kb search --team demo_team --query "output reconciliation retry"
```

For DOCX POC handling, the command should return a clear unsupported-format or
manual-transcript-required warning until a parser is intentionally added.

## API Workflow

The API should expose the same lifecycle:

```text
POST /intake/imports
GET  /intake/drafts?team_id=demo_team&status=pending
GET  /intake/drafts/{draft_id}
POST /intake/drafts/{draft_id}/review
POST /intake/drafts/{draft_id}/promote
POST /intake/eval
```

Upload responses should include the draft id, source hash, validation summary,
and artifact paths. Promotion responses should include the promoted document path
and retrieval refresh status.

## UI Workflow

The UI should support a simple review queue:

1. Upload or select local synthetic sample files.
2. Show detected source type, app, component, and proposed title.
3. Show source spans side by side with candidate claims.
4. Let reviewers approve, reject, quarantine, or request edits.
5. Promote approved drafts into the selected DemoCorp knowledge pack.
6. Run a retrieval smoke test from the promoted document.
7. Show whether the promoted source appears in context packs.

Reviewers should be able to edit metadata before promotion. The raw source file
and generated draft should remain immutable so the audit trail stays stable.

## Human Review Rules

The default policy is conservative:

- deterministic metadata can be proposed automatically
- semantic claims remain candidates until reviewed
- unsupported binary formats produce a draft warning, not a trusted document
- rejected or quarantined drafts are excluded from retrieval
- approved drafts can be promoted to knowledge packs or approved memory claims
- every promotion event records reviewer, timestamp, source hash, and reason

Reviewers should confirm:

- title and document type
- app and component metadata
- source spans for each important claim
- whether the content is operational guidance, architecture, testing guidance, or
  historical context
- whether the document conflicts with existing approved memory

## Artifact Isolation

Intake artifacts should be written under the configured artifact root:

```text
artifacts/intake/uploads/{team_id}/{source_id}/
artifacts/intake/drafts/{team_id}/{draft_id}.json
artifacts/intake/reviews/{team_id}/{draft_id}.json
artifacts/intake/promotions/{team_id}/{promotion_id}.json
```

Promotion to a knowledge pack should write only reviewed Markdown/YAML content.
Private teams should promote into private extension repositories, not the public
DREAM checkout. The public repo should keep only synthetic DemoCorp samples.

## No-Real-Connectors Boundary

The POC must not connect to real wiki, document storage, chat, ticketing, code
hosting, or email systems. "Import" means local file upload, pasted text, or
synthetic export file.

This keeps the demo focused on the memory workflow:

```text
source file -> structured draft -> human review -> promotion -> retrieval
```

Real connector work belongs in private extensions after authentication, ACL,
redaction, and data residency requirements are designed.

## Acceptance Guidance

A next-phase implementation is acceptable when:

- the runbook sample imports into a pending draft with runbook metadata
- the HLD export imports into a pending draft with architecture metadata
- the DOCX placeholder produces a clear parser-boundary warning
- each candidate claim cites a source span
- reviewers can approve, reject, quarantine, and promote drafts
- promoted drafts become searchable through the knowledge retriever
- rejected and quarantined drafts do not appear in context packs
- artifact paths stay under `DREAM_ARTIFACT_ROOT`
- no workflow requires a real enterprise connector
- all sample names remain synthetic DemoCorp names
