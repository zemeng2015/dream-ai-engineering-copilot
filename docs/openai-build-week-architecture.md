<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenAI Build Week Architecture and Safety Evidence

## One governed change loop

```text
change request
    |
    v
memory distillation + evidence graph
    |
    v
source-backed Jira draft (human approval boundary)
    |
    v
PR diff review against Jira + memory (advisory boundary)
    |
    v
GPT-5.6 JUnit 5 candidates (artifact isolation boundary)
    |
    v
deterministic rubrics + optional GPT-5.6 judge
    |
    v
audited summary and evidence paths
```

The orchestration entry point is `EngineeringLoopService`; the HTTP entry point
is `POST /engineering-loop/run`; the demo surface is `/engineering-loop` in the
Angular application.

## Meaningful OpenAI usage

- Codex: used to inspect the existing DREAM architecture, implement the native
  provider and orchestration layer, connect JTestGen, build the UI, add tests,
  and create the submission evidence.
- GPT-5.6: invoked through the OpenAI Responses API with configurable reasoning
  effort. It synthesizes the Jira draft, reviews the diff, produces structured
  JUnit 5 candidates, and can judge the resulting artifacts.
- Provider provenance is attached to stage results and the workflow audit log.

## Guardrails

- Memory claims retain source paths and pass a citation-validity evaluation.
- Jira output is a draft; unresolved questions block an automatic-ready status.
- PR review is advisory and requires a human reviewer.
- JTestGen validates paths and Java/JUnit structure, rejects traversal, and
  writes only below `artifacts/jtestgen/<run>/generated`.
- Evaluation uses deterministic rubrics even when the optional model judge is
  enabled.
- The loop does not create external Jira tickets, post PR comments, execute
  generated code, or merge changes.

## Verification path

```powershell
python -m pytest -q
python -m ruff check .
Set-Location frontend
npm ci
npm run build
```

For a credential-free judge run, start the API and UI, open
`http://localhost:4200/engineering-loop`, keep **Live GPT-5.6** disabled, and
select **Run engineering loop**. For the live run, configure `OPENAI_API_KEY`
and enable the toggle.
