<!-- SPDX-License-Identifier: Apache-2.0 -->

# Current Development Handoff

Last updated: 2026-07-06.

This file is the first stop for a new development conversation. It summarizes
the current local branch state after the UI simplification and live FastAPI
wiring work.

For product-planning context and the detailed raw-doc-to-structured-memory
implementation notes, read:

- `docs/recent-changes-planning-handoff.zh-CN.md`

## Branch and Runtime

- Branch: `codex/memory-hub-density-cleanup`
- Frontend: Angular app on `http://localhost:4300`
- Backend: FastAPI on `http://127.0.0.1:8000`
- FastAPI command:

```powershell
uvicorn dream.api.app:app --reload --host 127.0.0.1 --port 8000
```

- Frontend command:

```powershell
npm start --prefix frontend -- --host 127.0.0.1 --port 4300
```

## Current Product Surfaces

Primary routes:

- `/mission-control`
- `/memory`
- `/memory/:documentId`
- `/workbench`
- `/requirements`
- `/review`
- `/context/:caseId`
- `/codebase`
- `/audit`
- `/audit/:targetId`

Legacy mock routes redirect into the primary surfaces. Do not restore old mock
pages unless the product decision changes.

## Live Workflow State

- Memory Hub supports browser file upload and backend-visible local path
  registration, then exposes the full lifecycle: parse, edit draft metadata,
  approve, promote. Only `promoted` documents count as memory.
- `/memory/:documentId` shows the source detail view with raw source preview,
  parsed sections, source/hash/span provenance, normalized Markdown, review
  state, promoted path, structured draft review events, intake audit events, and
  downstream workflow runs that later consumed the promoted source. Review events
  cover metadata updates, review decisions, and promotion with field diffs,
  metadata snapshots, source hash, section hashes, reviewer notes, and linked
  audit run ids. Downstream usage includes matched source paths, match reason,
  structured match proofs with source hash and section span/hash evidence, and
  an Audit route when one can be inferred.
- `dream memory scan` and `/memory/scan` now attach intake provenance to
  document-derived `MemoryClaim` evidence. Claims produced from promoted intake
  docs include `evidence.intake_proofs` with `document_id`, `draft_id`,
  promoted/raw paths, source hash verification, intake audit run ids, and
  section hash/span proof, deterministic match explanation, and matched terms.
- Memory Hub has a Claim Review tab backed by `/memory/diff`,
  `/memory/conflicts`, `/memory/review`, and `/memory/ledger`. It can run a demo
  memory scan, list added/changed markers over latest-scan claims, show active
  single-value conflict pairs with raw-trace links, resolve a pair through the
  conservative `approve_winner_reject_other` action, show intake proof summaries,
  link back to `/memory/:documentId`, and write approve/reject/quarantine events
  into the durable memory ledger. Review ledger events now carry reviewer
  signatures, field-level governance diffs, claim snapshots, raw risk/conflict
  signals, and reviewer-readable signal explanations; conflict resolution events
  are stored in `memory-conflict-resolutions`.
- Promoted source documents expose `promoted_path` through `/intake/documents`.
- The current promoted synthetic runbook is:
  `knowledge_packs/demo_team/docs/runbooks/output-reconciliation-intake-demo-intake-5d2fff8695d5.md`
- Requirement Draft creates/analyzes a requirement case, generates a Jira draft,
  runs strict eval, links to `/audit/:evaluationId`, and links matched source
  rows back to `/memory/:documentId`.
- PR Review sends inline PR diff and Jira context text to `/review/pr`, runs
  strict eval, links to `/audit/:evaluationId`, and links matched source rows
  back to `/memory/:documentId`.
- `/context/:caseId` reads FastAPI context trail, context pack, and prompt
  preview APIs. It exposes retrieval steps, selected evidence, context-pack
  grouping, prompt preview, retrieval reasons, and source-detail links for
  matched intake documents. Memory claim references now preserve
  `intake_proofs`, so approved claims in context can still be traced back to
  raw intake documents, section hashes, intake audit runs, and claim/source
  match explanations.
- Codebase Index reads saved repo index JSON and file content through FastAPI.
- Audit & Eval detail reads `/eval/runs/{evaluation_id}`, including
  `markdown_report`, `json_path`, `markdown_path`, and `warnings`.
- Audit & Eval selected-run source chips link back to `/memory/:documentId` when
  a retrieved source path matches a registered intake document.

## Raw Doc To Structured Memory Snapshot

The current intake implementation is real FastAPI/backend code, not only a
frontend mock:

```text
POST /intake/documents
  -> computes source_hash and duplicate-content warnings
  -> artifacts/intake/uploads/<document_id>.<ext>
  -> artifacts/intake/documents/<document_id>.json

POST /intake/documents/upload
  -> accepts multipart browser file upload
  -> computes source_hash and duplicate-content warnings
  -> artifacts/intake/uploads/<document_id>.<ext>
  -> artifacts/intake/documents/<document_id>.json

GET /intake/documents/{document_id}/detail
  -> raw source preview, source hash verification, draft, promoted path, draft review events, intake audit events, downstream usage events/usages, match proofs

POST /intake/documents/{document_id}/parse
  -> parsed sections include source_span, source_reference, and section_hash
  -> artifacts/intake/drafts/<draft_id>/draft.json
  -> artifacts/intake/drafts/<draft_id>/draft.md

GET /intake/drafts/{draft_id}
  -> returns parsed sections, proposed metadata, concepts, provenance, and markdown

GET /intake/drafts/{draft_id}/review-events
  -> structured metadata/review/promote event ledger with field diffs and audit run ids

PATCH /intake/drafts/{draft_id}/metadata
  -> updates title, document type, app, component, concepts
  -> regenerates draft.md before approval/promotion
  -> writes review-events/<event_id>.json with metadata diff

POST /intake/drafts/{draft_id}/review
  -> draft review_status updated to approved/rejected/etc.
  -> writes review-events/<event_id>.json with status diff

POST /intake/drafts/{draft_id}/promote
  -> knowledge_packs/<team_id>/docs/<document_type>/<title>-<document_id>.md
  -> writes review-events/<event_id>.json with promoted path diff

POST /memory/scan
  -> document-derived MemoryClaim evidence includes intake_proofs
  -> review queue/diff markdown shows the intake document id and match explanation for traced claims
GET /memory/conflicts
  -> active single-value conflict pairs include both claims, effective statuses, latest reviews, evidence paths, intake ids, and explanation
POST /memory/conflicts/resolve
  -> approve selected winner, reject the other side, append normal review events plus conflict resolution event
GET /memory/conflict-resolutions
  -> dedicated conflict resolution ledger
```

Key code:

- `dream/intake/service.py`
- `dream/intake/repository.py`
- `dream/intake/parsers.py`
- `dream/intake/models.py`
- `dream/memory/models.py`
- `dream/memory/distiller.py`
- `dream/memory/claim_retriever.py`
- `frontend/src/app/features/memory-hub/`
- `frontend/src/app/features/memory-document-detail/`
- `frontend/src/app/core/dream-api.service.ts`

Important product caveat: browser upload is local POC multipart upload, not a
real enterprise document connector. `document_type` should also match folders
listed in `knowledge_packs/<team_id>/team.yaml` or promoted documents may not be
loaded by the knowledge retriever.

Remaining high-value gaps: add supersede/merge-style conflict actions and design
connector ACL/redaction/audit policy before real enterprise sources are
attached.

## Known Limits

- `npm run build` succeeds but reports the existing
  `codebase-memory.component.scss` style budget warning.
- Human Rating in Audit & Eval is persisted through
  `/audit/runs/{run_id}/ratings` and the SQLite `human_ratings` table.
- PR Review currently uses `dfp-demo-repo` as the frontend default repo name.
- Windows Git may warn that LF will be replaced by CRLF.
- `docs/frontend-runbook/` contains historical generated artifacts and must be
  regenerated before a new UI acceptance pass.

## Verification Commands

```powershell
python -m ruff check .
python -m pytest
```

Raw doc to structured memory acceptance:

```powershell
python scripts/verify_raw_doc_memory_flow.py
```

```powershell
cd frontend
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
```

## Documentation To Keep In Sync

- `docs/recent-changes-planning-handoff.zh-CN.md`
- `README.md`
- `docs/frontend-angular.md`
- `docs/knowledge-intake-pipeline.md`
- `docs/codebase-memory.md`
- `docs/evaluation-agent.md`
- `docs/frontend-runbook/README.md`
- `docs/frontend-runbook/regression-20260703-memory-ui/frontend-regression-report.md`
