<!-- SPDX-License-Identifier: Apache-2.0 -->

# Angular Frontend

DREAM includes an Angular 19 frontend under `frontend/`. The current UI is a
live FastAPI workbench, not a mock-only route gallery.

## Current Routes

Primary navigation exposes five product surfaces:

| Route | Purpose |
| --- | --- |
| `/mission-control` | Work queue and primary start actions. |
| `/memory` | Source intake lifecycle and codebase index summary. |
| `/workbench` | Default engineering workbench, starting in Jira draft mode. |
| `/requirements` | Engineering workbench opened directly in Jira draft mode. |
| `/review` | Engineering workbench opened directly in PR review mode. |
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

The FastAPI app allows `http://localhost:4300` and `http://127.0.0.1:4300` for
local CORS.

## Live Workflows

- Mission Control reads FastAPI intake documents, requirement cases, audit
  records, eval scorecards, and codebase files.
- Memory Hub can register a local source, parse it, approve it, promote it into
  `knowledge_packs`, and show the promoted structured Markdown path.
- Codebase Index reads saved repo index JSON, repo files, file content, concepts,
  search results, and impact map data from FastAPI.
- Requirement Draft creates a requirement case, analyzes context, generates a
  Jira proposal, runs strict eval, and links to `/audit/:evaluationId`.
- PR Review sends inline PR diff and Jira context text to FastAPI, runs strict
  eval, and links to `/audit/:evaluationId`.
- Audit & Eval reads stored eval scorecards and audit runs. Human Rating is still
  local UI state and is not persisted by FastAPI.

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
