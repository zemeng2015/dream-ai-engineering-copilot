<!-- SPDX-License-Identifier: Apache-2.0 -->

# DREAM Angular Workbench

This Angular frontend is the mock-data workbench for DREAM - Domain-aware
Requirements, Engineering Automation & Memory.

It demonstrates the main DREAM product flows with synthetic DemoCorp Forecast
Platform data:

- Mission Control dashboard
- Knowledge Memory search
- Codebase Memory search
- Requirement Case analysis with evidence, impact map, role questions, Jira draft, and eval scorecard
- PR Review with changed files, related codebase memory, review notes, and eval scorecard
- Eval & Audit with deterministic scorecards and human ratings
- TestGen Stub, with no repository writes and no unit-test generation engine
- Settings / guardrail preview

All data is synthetic DemoCorp mock data. No real company data, real Jira
tickets, real pull requests, real logs, real API endpoints, or real repository
paths are included.

## Development

```bash
npm install
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
npm start
```

By default Angular serves at `http://localhost:4200/`. If that port is already
occupied, use another free port:

```bash
npm start -- --host 127.0.0.1 --port 5000
```

You can also preview a built bundle:

```bash
npm run build
cd dist/frontend/browser
python -m http.server 5000 --bind 127.0.0.1
```

## Real OpenAI Mode

Requirement Case and PR Review include an execution mode selector:

- `Mock local provider`
- `Real FastAPI + OpenAI-compatible provider`

For real mode, start FastAPI separately with `OPENAI_API_KEY` or
`OPENAI_COMPATIBLE_API_KEY` set in the backend environment:

```bash
python -m uvicorn dream.api.app:app --host 127.0.0.1 --port 8000
```

The Angular app does not read or store the API key.

## Design Direction

The UI uses an enterprise mortgage-finance-inspired style: deep navy
navigation, white and pale blue-gray surfaces, teal/cyan action accents,
compact evidence tables, clear status pills, and explicit human-review gates.
It does not use real company logos, trademarks, imagery, or brand assets.

Motion is limited to purposeful page entry, card rise, status pulse, and scan
line effects. `prefers-reduced-motion` disables animation.

## Guardrails

- MockLLMProvider is the default.
- OpenAI-compatible generation is not called by the frontend.
- Generated requirement and PR outputs are draft/review-aid only.
- TestGen remains a provider interface/stub and does not generate unit tests.
