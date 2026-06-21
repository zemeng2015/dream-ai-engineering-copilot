<!-- SPDX-License-Identifier: Apache-2.0 -->

# Angular Frontend

DREAM includes an Angular mock-data workbench under `frontend/`.

## Long-Term Goal

Build a production-ready enterprise frontend for DREAM that can start with local
mock data and later connect to the FastAPI API without changing the user-facing
workflows.

## Phase 1 Scope

- Dashboard
- Knowledge Base search
- Requirement Draft generation
- PR Review summary generation
- TestGen Stub workflow
- Audit & Eval with human rating
- Settings and guardrail visibility

The TestGen page does not generate unit tests, write files, run Maven, or call an
external JTestGen command. It only validates the provider workflow surface.

## Design System

The frontend uses a conservative enterprise visual system:

- Deep navy app shell
- Teal primary actions
- Cool gray background
- White data surfaces
- 8px maximum radius
- Dense tables
- Clear status pills
- Visible focus states
- Typed reactive forms

The style is inspired by mortgage-finance enterprise web applications, but it
does not copy third-party branding or assets.

## Commands

```bash
cd frontend
npm install
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
npm start
```

Open `http://localhost:4200/`.

## Future Integration

Planned next steps:

- Add API adapter service for FastAPI endpoints.
- Add `GET /kb/teams` and `POST /kb/search` backend endpoints.
- Add `POST /testgen/plan` and `POST /eval/rate` backend endpoints.
- Replace mock service calls route-by-route.
- Add Playwright e2e smoke tests.

