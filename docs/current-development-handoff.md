<!-- SPDX-License-Identifier: Apache-2.0 -->

# Current Development Handoff

Last updated: 2026-07-04.

This file is the first stop for a new development conversation. It summarizes
the current local branch state after the UI simplification and live FastAPI
wiring work.

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
- `/workbench`
- `/requirements`
- `/review`
- `/codebase`
- `/audit`
- `/audit/:targetId`

Legacy mock routes redirect into the primary surfaces. Do not restore old mock
pages unless the product decision changes.

## Live Workflow State

- Memory Hub registers local source documents and now exposes the full lifecycle:
  parse, approve, promote. Only `promoted` documents count as memory.
- Promoted source documents expose `promoted_path` through `/intake/documents`.
- The current promoted synthetic runbook is:
  `knowledge_packs/demo_team/docs/runbooks/output-reconciliation-intake-demo-intake-5d2fff8695d5.md`
- Requirement Draft creates/analyzes a requirement case, generates a Jira draft,
  runs strict eval, and links to `/audit/:evaluationId`.
- PR Review sends inline PR diff and Jira context text to `/review/pr`, runs
  strict eval, and links to `/audit/:evaluationId`.
- Codebase Index reads saved repo index JSON and file content through FastAPI.
- Audit & Eval detail reads `/eval/runs/{evaluation_id}`, including
  `markdown_report`, `json_path`, `markdown_path`, and `warnings`.

## Known Limits

- `npm run build` succeeds but reports the existing
  `codebase-memory.component.scss` style budget warning.
- Human Rating in Audit & Eval is frontend-local state, not persisted.
- PR Review currently uses `dfp-demo-repo` as the frontend default repo name.
- Windows Git may warn that LF will be replaced by CRLF.
- `docs/frontend-runbook/` contains historical generated artifacts and must be
  regenerated before a new UI acceptance pass.

## Verification Commands

```powershell
python -m ruff check .
python -m pytest
```

```powershell
cd frontend
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
```

## Documentation To Keep In Sync

- `README.md`
- `docs/frontend-angular.md`
- `docs/knowledge-intake-pipeline.md`
- `docs/codebase-memory.md`
- `docs/evaluation-agent.md`
- `docs/frontend-runbook/README.md`
- `docs/frontend-runbook/regression-20260703-memory-ui/frontend-regression-report.md`
