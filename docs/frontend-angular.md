<!-- SPDX-License-Identifier: Apache-2.0 -->

# Angular Frontend

DREAM includes an Angular 21 frontend under `frontend/`. The current UI is a
live FastAPI workbench, not a mock-only route gallery.

## Current Routes

Primary navigation exposes five product surfaces:

| Route | Purpose |
| --- | --- |
| `/mission-control` | Work queue and primary start actions. |
| `/memory` | Source intake lifecycle, memory claim review, and codebase index summary. |
| `/memory/:documentId` | Source detail with raw preview, structured draft, provenance, audit events, and downstream usage. |
| `/workbench` | Default engineering workbench, starting in Jira draft mode. |
| `/requirements` | Engineering workbench opened directly in Jira draft mode. |
| `/review` | Engineering workbench opened directly in PR review mode. |
| `/context/:caseId` | Retrieval context trail with context pack, prompt preview, source reasons, and raw source links. |
| `/codebase` | Repo browser and saved codebase index JSON. |
| `/audit` | Eval agent list, selected case detail, audit runs, and human rating UI. |
| `/audit/:targetId` | Case-by-case eval detail route. |

Legacy routes such as `/knowledge`, `/knowledge-intake`, `/graph`,
`/context-intelligence`, `/trust`, `/settings`, and `/testgen` redirect into the
current primary surfaces. Their old standalone mock components remain in the
tree only as historical implementation references.

## Runtime Dependencies

Run FastAPI on port 8000:

```powershell
uvicorn dream.api.app:app --reload --host 127.0.0.1 --port 8000
```

Run Angular on port 4300 for the current demo and runbook tooling:

```powershell
cd frontend
npm install
npm start -- --host 127.0.0.1 --port 4300
```

The FastAPI app allows local Angular origins on ports 4200, 4201, 4300, 4310,
and 5000 for local CORS. Add comma-separated production frontend origins with
`DREAM_CORS_ORIGINS` when serving the UI from a different host.

## Live Workflows

- Mission Control reads FastAPI intake documents, requirement cases, audit
  records, eval scorecards, and codebase files.
- Memory Hub can upload a browser file or register a backend-visible source,
  parse it, edit draft metadata, approve it, promote it into `knowledge_packs`,
  and show the promoted structured Markdown path. The metadata editor displays a
  compact provenance summary from the draft source hash, section count, and span
  count. Source rows link to `/memory/:documentId` for raw source preview,
  parsed section spans/hashes, normalized Markdown, review state, promoted path,
  structured review events, intake audit events, and downstream workflow usage
  after promotion. Review events show metadata diffs, reviewer notes, source
  hash, section hash count, and linked audit run ids. Downstream usage rows show
  matched paths, match reason, structured match proofs with hash and section
  span/hash evidence, and an Audit detail link when available.
- Memory Hub Claim Review reads `/memory/diff`, `/memory/conflicts`, and
  `/memory/ledger`, can run `/memory/scan`, and writes approve/reject/quarantine
  decisions through `/memory/review`. Claim rows come from the latest scan, with
  diff markers for added/changed claims, and show evidence paths plus intake
  proof summaries with source-detail links when the claim came from a promoted
  intake document. Active single-value conflict pairs are shown above the claim
  queue with both values, effective statuses, source summaries, raw-trace links,
  and a "Keep this" resolution action that calls `/memory/conflicts/resolve`.
  Latest review rows also surface structured inline review proof:
  decision metadata, reviewer signature, field-level governance diffs, claim
  snapshot, risk/conflict signals with reviewer-readable explanations and
  evidence, deterministic match explanation, matched terms, and raw-trace source
  links.
- Codebase Index reads saved repo index JSON, repo files, file content, concepts,
  search results, and impact map data from FastAPI.
- Requirement Draft creates a requirement case, analyzes context, generates a
  Jira proposal, runs strict eval, and links to `/audit/:evaluationId`.
  Requirement source rows link back to `/memory/:documentId` when they match a
  registered intake document.
- PR Review sends inline PR diff and Jira context text to FastAPI, runs strict
  eval, and links to `/audit/:evaluationId`. PR source rows link back to
  `/memory/:documentId` when they match a registered intake document.
- Audit & Eval reads stored eval scorecards and audit runs. Human Rating now
  reads and writes `/audit/runs/:runId/ratings`, so reviewer scores are persisted
  through FastAPI/SQLite instead of browser-local state. Source chips in selected
  audit runs link back to `/memory/:documentId` when the retrieved path matches
  an intake document.
- Context Trail reads `/context/trails/:caseId`, `/context/packs/:caseId`, and
  `/context/prompt-preview/:caseId`. It shows retrieval steps, selected evidence,
  context-pack grouping, retrieval reasons, prompt preview, and source-detail
  links for matched intake documents.

## Validation Commands

```powershell
python -m pytest
python -m ruff check .
```

```powershell
cd frontend
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
```

Known warning: `npm run build` currently reports
`codebase-memory.component.scss` over the Angular component style budget. The
build still succeeds.

## Runbook Regeneration

The runbook artifacts under `docs/frontend-runbook/` are generated from browser
screenshots and an annotation manifest. Regenerate them only after the local app
is running on port 4300:

```powershell
node docs/frontend-runbook/capture_screenshots_cdp.mjs
python docs/frontend-runbook/annotate_screenshots.py
python docs/frontend-runbook/generate_runbooks.py
```
