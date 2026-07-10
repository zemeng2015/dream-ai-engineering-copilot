<!-- SPDX-License-Identifier: Apache-2.0 -->

# DREAM Leadership Demo Runbook

This runbook operates the provider-neutral DREAM leadership scenario. It uses
only synthetic DemoCorp Forecast Platform data and performs no Jira, GitHub, or
other external writes.

## Fixed Scenario Contract

| Field | Fixed value |
|---|---|
| Team | `demo_team` |
| Repository | `dfp-demo-repo` |
| Repository path | `examples/dfp-demo-repo` |
| Requirement case | `case-leadership-async-status` |
| Memory scan | `leadership-dfp-memory-v1` |
| Eval profile | `async-status-tracking` |
| Application | `ForecastDemo` |
| Component | `ExecutionMonitor` |

The rough request asks for task-level visibility and automatic refresh when a
forecast execution takes too long. Reset always recreates the same case, scan,
approved claim, Context Trail identifier, and source paths.

## Pre-Demo Reset

From the repository root:

```powershell
python scripts/seed_leadership_demo.py --reset
```

The command:

1. indexes only `examples/dfp-demo-repo`;
2. builds the DFP Evidence Graph;
3. creates the fixed memory scan;
4. approves the source-backed `execution status` architecture claim;
5. creates and analyzes the fixed Requirement Case;
6. answers all seeded questions except one BE status-transition decision;
7. generates the Engineering Brief and Jira draft;
8. builds the Context Trail and Context Pack; and
9. runs the deterministic Jira-draft evaluation.

The JSON result must report:

- `case_id = case-leadership-async-status`;
- `repo_name = dfp-demo-repo`;
- exactly one `open_question_id`;
- `jira_ready = false`; and
- no source path containing `java-demo-repo`.

Running without `--reset` intentionally fails when the fixed case already
exists. This prevents accidental mutation of an in-progress demonstration.

## Start the Product

The checked-in configuration resolves the Leadership/Workbench `config`
selector to `mock`, so the safe default makes no external model call. For an
explicit synthetic local GPT-5.4 run, set these variables in Terminal 1 before
starting the backend:

```powershell
$env:DREAM_LLM_PROVIDER="openai-compatible"
$env:OPENAI_COMPATIBLE_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_COMPATIBLE_MODEL="gpt-5.4"
# OPENAI_API_KEY must already be configured in the local environment.
```

Do not use this override with real organization sources until the endpoint and
data flow are approved. Removing `DREAM_LLM_PROVIDER` returns the product to the
checked-in mock default.

Terminal 1:

```powershell
python -m uvicorn dream.api.app:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm start
```

Open:

```text
http://localhost:4200/leadership-demo
```

The default shell must display `Provider Neutral` and `Human-Gated`. Qwen and
Alibaba labels belong only to the explicit `/hackathon-demo` profile.

## Ten-Minute Leadership Flow

### 0:00–1:00 — Problem and Positioning

Use the Leadership page hero and comparison table.

> DREAM is not another chatbot. It supplies governed organizational memory to
> engineering workflows and preserves the evidence and uncertainty behind each
> delivery decision.

### 1:00–2:00 — Governed Memory

Open Memory Hub and locate the approved `execution status` claim. Show:

- reviewer identity;
- architecture source path;
- approved status; and
- claim/review ledger proof.

Candidate, rejected, quarantined, and unresolved conflicting claims must not
enter generation.

### 2:00–5:00 — Rough Request to Requirement Case

Open Engineering Workbench and load `case-leadership-async-status`. Show:

- the original rough request;
- DFP backend and frontend files;
- incident, Jira, PR, runbook, and test evidence;
- role-specific questions; and
- the generated Jira draft.

Do not read the whole draft. Emphasize concrete DFP impact and missing decisions.

### 5:00–6:30 — Human Gate

Keep the seeded BE status-transition question open. Jira readiness must remain
blocked. Explain that DREAM preserves ambiguity instead of silently completing
the specification.

For a live completion demonstration, answer or explicitly waive that question,
regenerate the Jira draft, and show Jira-ready status. Run the reset command
afterward to restore the baseline.

### 6:30–8:00 — Context and Source Proof

Open:

```text
/context/case-leadership-async-status
```

Trace one output decision through:

```text
Generated decision
→ selected approved MemoryClaim
→ reviewer and governance status
→ status-tracking architecture source
→ related DFP code/tests/incidents
→ prompt preview
```

### 8:00–9:00 — Eval and Audit

Open Audit & Eval. Show the deterministic scorecard, missing items, source
coverage, warnings, model/provider record, and human-rating surface.

Do not claim that Human Rating changes future ranking. Ratings are persisted but
the learning policy remains future work.

### 9:00–10:00 — Pilot Ask

Ask for a six-week controlled discovery pilot:

- one team;
- one application;
- one repository;
- read-only approved sources;
- no automatic Jira or PR writes;
- human approval required; and
- exit if trust, usefulness, or data-boundary gates fail.

## Success Measures

- time from rough request to first engineering draft;
- critical clarification questions found before implementation;
- impact-map recall against an SME-reviewed golden set;
- valid source-citation rate;
- unsupported reference count;
- human edit distance before handoff;
- BA/TL/QA usefulness ratings; and
- zero data-boundary violations.

## Fallback Plan

1. Run the reset and seed command before the meeting, not during it.
2. Keep the API and Angular processes running locally or inside the approved
   private deployment boundary.
3. If generation is unavailable, use the already seeded fixed case, Context
   Trail, Jira draft, and Eval artifacts; they are deterministic local outputs.
4. If the UI becomes unavailable, show the generated Markdown/JSON artifacts
   under `artifacts/requirement-cases`, `artifacts/context-trails`, and
   `artifacts/evals`.
5. Never switch to the Hackathon/Qwen route as a leadership fallback; it changes
   the provider and deployment narrative.

## Verification

Run the one-command product gate first:

```powershell
python scripts/run_leadership_preflight.py --require-frontend-bundle
```

Then run the deterministic human-gate rehearsal:

```powershell
python scripts/run_leadership_rehearsal.py
```

The rehearsal starts from the fixed blocked state, answers the one material
backend transition question, proves Jira readiness, regenerates Context/Eval/
Audit proof, and restores the blocked baseline. Its report is written under
`artifacts/leadership-rehearsal/`. It does not call an external provider or write
to Jira, GitHub, deployment, email, or messaging systems.

For the final presentation commit, follow
[Leadership Presentation Release Process](leadership-release-process.md) and
verify the strict release manifest before opening the meeting.

Before presenting a frozen commit, add `--strict-git`. The command resets the
fixed scenario, proves approved-claim consumption, human gate, synthetic source
boundary, Context/Eval/Audit artifacts, provider-profile isolation, required
docs, Angular bundle, and a three-repetition paired harness. It writes JSON and
Markdown under `artifacts/leadership-preflight/` and exits non-zero on failures.

```powershell
python -m pytest tests/test_leadership_demo.py -q
python -m pytest tests/test_leadership_rehearsal.py -q
python -m pytest tests/test_leadership_preflight.py -q
python -m pytest -q
cd frontend
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
```

The seed acceptance test executes two consecutive resets and proves that the
fixed IDs and source paths remain stable without accumulating case-scoped Audit,
Eval, or claim-review records.

Validate the paired benchmark harness separately:

```powershell
python scripts/run_leadership_ab_benchmark.py --provider fixture
python -m pytest tests/test_leadership_benchmark.py -q
```

The fixture result is operational fallback proof only. Before presenting an A/B
quality claim, run the approved provider through the live-model procedure and
apply the acceptance gates in
[Leadership Paired A/B Benchmark](leadership-ab-benchmark.md).

## Explicit Limitations

- The dataset is synthetic and is not evidence of production ROI.
- The provider-neutral product harness is implemented, but its fixture result is
  not model-quality evidence. No Fannie-facing live-model result is claimed yet.
- The Qwen paired benchmark is competition evidence and remains separate from
  the leadership product evidence baseline.
- Exact retrieval Recall@12 is 35.6% and remains a known bottleneck.
- Enterprise SSO, ACL-aware retrieval, connectors, redaction policy, data
  residency, and production storage belong to the controlled Pilot boundary.
- Human ratings are stored but do not yet change future retrieval or policy.
