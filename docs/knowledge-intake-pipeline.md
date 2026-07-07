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

## Current Implementation Snapshot

The current branch has a real local-file implementation behind FastAPI and the
Memory Hub UI. It is intentionally conservative:

```text
Upload browser file or register local file path
  -> copy raw file into artifacts/intake/uploads/
  -> compute source hash and warn on duplicate content
  -> write IntakeDocument JSON under artifacts/intake/documents/
  -> parse into KnowledgeDraft sections, source spans, section hashes, concepts, and normalized Markdown
  -> write draft.json and draft.md under artifacts/intake/drafts/
  -> reviewer can edit title, doc type, app, component, and concepts
  -> human review updates review_status
  -> metadata updates, review decisions, and promotion write draft review events with field diffs
  -> promote writes reviewed Markdown into knowledge_packs/<team>/docs/<type>/
  -> detail view exposes raw source, draft, provenance, review events, audit events, and downstream usage
  -> memory scan turns promoted docs into governed MemoryClaim candidates with intake proof
```

Key code paths:

- `dream/intake/service.py`
- `dream/intake/repository.py`
- `dream/intake/parsers.py`
- `dream/intake/models.py`
- `dream/api/routes.py`
- `frontend/src/app/features/memory-hub/`
- `frontend/src/app/features/memory-document-detail/`
- `frontend/src/app/core/dream-api.service.ts`

Current status transitions:

```text
uploaded -> parsed -> approved -> promoted
```

The current UI supports browser-native multipart upload and still keeps backend
local path registration as a dev/demo fallback. It does not yet implement
drag-and-drop upload, connector import, or remote document fetch.

## Source Types

| Source type | POC input | Normalization |
| --- | --- | --- |
| Runbook | `examples/intake-samples/runbook-output-reconciliation.md` | Markdown with front matter and headings |
| Confluence HLD export | `examples/intake-samples/confluence-hld-forecast-orchestration-export.md` | Markdown plus HTML-like blocks |
| DOCX | `examples/intake-samples/docx-placeholder/README.md` | Parser support exists for local `.docx` files, but the public repo only ships a placeholder instead of binary sample data |

The Confluence sample is an exported file, not a live Confluence connector. The
DOCX placeholder documents the expected behavior without committing binary test
data. A real local `.docx` file can be parsed by extracting paragraph text from
`word/document.xml`, but rich formatting, tables, comments, and embedded images
are not modeled yet.

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

The current CLI uses explicit upload, parse, review, and promotion verbs.

```bash
dream intake upload \
  --team demo_team \
  --file examples/intake-samples/runbook-output-reconciliation.md \
  --type runbooks \
  --title "Output Reconciliation Intake Demo"

dream intake upload \
  --team demo_team \
  --file examples/intake-samples/confluence-hld-forecast-orchestration-export.md \
  --type architecture

dream intake list
dream intake parse --document <document_id>

dream intake review \
  --draft <draft_id> \
  --status approved \
  --reviewer demo.lead \
  --reason "Synthetic runbook matches DemoCorp recovery policy."

dream intake promote --draft <draft_id>
dream kb search --team demo_team --query "output reconciliation retry"
```

For DOCX POC handling, the command should return a clear unsupported-format or
manual-transcript-required warning until a parser is intentionally added.

## API Workflow

The API exposes the same lifecycle:

```text
POST /intake/documents
POST /intake/documents/upload
GET  /intake/documents
GET  /intake/documents/{document_id}
GET  /intake/documents/{document_id}/detail
POST /intake/documents/{document_id}/parse
GET  /intake/drafts/{draft_id}
GET  /intake/drafts/{draft_id}/review-events
PATCH /intake/drafts/{draft_id}/metadata
POST /intake/drafts/{draft_id}/review
POST /intake/drafts/{draft_id}/promote
```

Upload responses include an intake document with a `sha256:<digest>` source
hash. The current local-file POC does not yet return draft id or a full
validation summary at upload time. Browser-uploaded documents use an
`uploaded://<filename>` original path and are copied into the same intake upload
artifact folder. If the same team uploads identical content again, the document
is accepted with a duplicate-content warning. Promotion responses include
`promoted_path`, and `GET /intake/documents` also returns `promoted_path` for
promoted documents.

Current FastAPI behavior:

- `POST /intake/documents` calls `KnowledgeIntakeService.upload_local_file(...)`.
- `POST /intake/documents/upload` accepts multipart files and calls
  `KnowledgeIntakeService.upload_file_content(...)`.
- `GET /intake/documents/{document_id}/detail` returns the intake document,
  optional draft, raw source preview, raw byte size, source hash verification,
  promoted path, intake audit events whose run ids match the document/draft,
  structured draft review events with metadata snapshots, field diffs, source
  hash, section hashes, reviewer notes, and linked audit run ids,
  downstream audit events whose retrieved sources match the promoted doc, and
  structured downstream usage records with matched paths, match reason, source
  hash/span/section match proofs, and an Audit route when available.
- `POST /intake/documents/{document_id}/parse` calls the deterministic parser.
- `GET /intake/drafts/{draft_id}` returns parsed sections, concepts, proposed
  metadata, and normalized Markdown.
- `GET /intake/drafts/{draft_id}/review-events` returns the structured
  metadata/review/promote event ledger for that draft.
- Parsed sections include `source_span` line numbers, `source_reference`, and
  `section_hash`. Normalized Markdown includes the source hash and section
  provenance lines.
- `PATCH /intake/drafts/{draft_id}/metadata` updates title, target document
  type, app, component, and concepts, then regenerates normalized Markdown and
  writes a `metadata_update` review event.
- `POST /intake/drafts/{draft_id}/review` records the human decision and writes
  a `review_decision` review event.
- `POST /intake/drafts/{draft_id}/promote` writes normalized Markdown into the
  knowledge pack and writes a `promotion` review event.
- Each step records an audit run with use cases
  `knowledge_intake_upload`, `knowledge_intake_parse`,
  `knowledge_intake_metadata_update`, `knowledge_intake_review`, and
  `knowledge_intake_promote`.
- `POST /memory/scan` reads promoted knowledge-pack Markdown. Claims derived
  from promoted intake documents include `evidence.intake_proofs` with the
  intake document id, draft id, raw/promoted paths, source hash verification,
  intake audit run ids, section-level span/hash proof, deterministic match
  explanation, and matched terms. Memory diff/review markdown shows the intake
  document id and match explanation for those claims.

## UI Workflow

The UI should support a simple review queue:

1. Upload or register a local synthetic sample file.
2. Parse the source into a structured draft.
3. Edit proposed metadata when needed.
4. Approve the draft from Memory Hub.
5. Promote the approved draft into `knowledge_packs`.
6. Show the promoted structured Markdown file in Memory Hub.
7. Run a memory scan and review document-derived claim candidates.
8. Use approved memory claims and promoted documents in retrieval, Jira drafting,
   PR review, and eval.

Reviewers should be able to edit metadata before promotion. The raw source file
and generated draft should remain immutable so the audit trail stays stable.

Current Memory Hub behavior:

- Source Intake tab lists registered docs.
- Rows show the next available action: Parse, Approve, or Promote.
- Promoted docs move into "Structured Docs in Memory".
- Every source row links to `/memory/:documentId`, where reviewers can inspect
  raw source preview, structured Markdown, parsed section spans/hashes, review
  state, structured review events, promoted path, matching intake audit events,
  and downstream workflow usage after promotion. Review events show metadata
  diffs, reviewer notes, source hash, section hash count, and the linked audit
  run. Downstream rows show matched paths, match reason, source
  hash/span/section match proofs, and an Audit detail link when available.
- Audit & Eval source chips link back to `/memory/:documentId` when a selected
  audit run's retrieved source path matches a registered intake document.
- Requirement Draft and PR Review source rows also link back to
  `/memory/:documentId` when their retrieved source path matches a registered
  intake document.
- Context Trail detail at `/context/:caseId` shows retrieval steps, selected
  evidence, context-pack grouping, prompt preview, and source-detail links for
  matched intake documents. Memory claim references in context responses carry
  `intake_proofs`, preserving raw document, audit run, source hash, and section
  proof when approved claims are selected for context.
- Parsed and approved docs expose a Draft Metadata editor for title, document
  type, app, component, and concepts.
- The Draft Metadata editor surfaces a compact provenance summary with source
  hash, section count, and span count.
- Claim Review tab reads memory diff and ledger state, can run a memory scan,
  shows latest-scan claims with added/changed markers, evidence paths, and
  intake proof summaries, and writes approve/reject/quarantine decisions back to
  the durable memory ledger. Ledger events now include reviewer signature,
  field-level governance diffs, claim snapshot, raw risk/conflict signals, and
  reviewer-readable signal explanations; the UI shows structured inline proof
  beside the latest decision. `/memory/conflicts` also exposes active
  single-value conflict pairs with both claims, effective statuses, latest
  reviews, evidence paths, intake document ids, and conflict explanations; the
  Claim Review UI displays those pairs with raw-trace source links and can call
  `/memory/conflicts/resolve` to approve the selected winner, reject the other
  side, and append a dedicated conflict resolution audit event.
- The Add Source Document form is collapsed by default and asks for team,
  document type, optional title, browser file, and optional backend file path.
- The Codebase Index tab is separate from Source Intake so the homepage does not
  duplicate detailed memory management.

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

## Current Gaps To Plan

- Add drag-and-drop upload and pasted-text intake on top of browser file upload.
- Normalize `document_type` values so promoted folders match `team.yaml`
  `document_paths`; otherwise retrieval may miss promoted files.
- Extend the basic `approve_winner_reject_other` resolution workflow with
  supersede/merge actions and more explicit field-level conflict decisions.

## End-to-End Acceptance Script

Run the raw-doc acceptance flow with:

```powershell
python scripts/verify_raw_doc_memory_flow.py
```

The script creates an isolated temporary knowledge-pack copy, artifact root, and
SQLite audit database, then verifies:

- local raw doc registration with source hash
- deterministic parse with source spans and section hashes
- metadata update, review decision, and promotion review events with field diffs
- promoted Markdown retrieval by a downstream requirement draft run
- audit run source tracking and source-detail downstream usage proof
- memory scan `intake_proofs` with raw/promoted paths, source hash, section
  proof, match explanation, and matched terms
- memory claim review and context trail reuse of the raw document proof

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
