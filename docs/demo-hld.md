<!-- SPDX-License-Identifier: Apache-2.0 -->

# DREAM Demo HLD

## 1. Product Summary

DREAM is a codebase-aware engineering memory platform for software teams. It
turns incomplete business requests and PR diffs into source-backed engineering
artifacts that humans can review.

The demo focuses on two high-value workflows:

1. A vague business request becomes a Requirement Case, Engineering Brief, and
   Jira-ready draft.
2. A fake PR diff becomes an AI-generated PR review aid with codebase memory,
   test awareness, audit, and evaluation.

DREAM is not a generic chatbot. Its value comes from structured team knowledge,
codebase memory, impact mapping, role-specific questions, audit, and eval.

## 2. Demo World

The demo uses only synthetic DemoCorp data.

- Product: DemoCorp Forecast Platform, or DFP
- App: ForecastDemo
- Repo: `examples/dfp-demo-repo`
- Domain objects: Job, Workflow, Task, Execution
- Layers: Angular-like frontend, Java backend, AWS-style orchestration, Python processors
- Roles: BA, TL, FE, BE, QA, OPS

No real company data, real Jira tickets, real PRs, real endpoints, or real logs
are included.

## 3. Core Product Functions

### 3.1 Knowledge Pack Retrieval

DREAM loads a team knowledge pack from Markdown files and `team.yaml`.

Knowledge includes:

- domain docs
- architecture docs
- runbooks
- historical incidents
- historical Jira stories
- historical PR notes
- testing docs
- PR review checklists
- concept memory docs

Demo command:

```bash
dream kb search --team demo_team --query "execution status stuck running"
```

### 3.2 Codebase Memory

DREAM scans a local repo and creates a structured JSON index.

The index stores:

- files
- languages
- file roles
- Java/Python/TypeScript symbols
- concepts
- source-to-test mappings
- simple dependencies
- summaries

Demo command:

```bash
dream codebase index \
  --team demo_team \
  --repo examples/dfp-demo-repo \
  --name dfp-demo-repo

dream codebase search \
  --team demo_team \
  --repo dfp-demo-repo \
  --query "status tracker batch task"
```

### 3.3 Requirement Case Workflow

A Requirement Case starts with a vague request and creates a source-backed
engineering analysis package.

Inputs:

- team id
- rough request
- optional requester role
- optional app/component

Outputs:

- retrieved context
- impact map
- role-specific clarification questions
- engineering brief
- Jira-ready draft
- audit records
- eval scorecards

Demo commands:

```bash
dream req create \
  --team demo_team \
  --request "Users say forecast jobs sometimes run for too long. The execution page should tell them which task is still running and refresh automatically, but the exact status labels and timeout behavior are not clear." \
  --role BA \
  --app ForecastDemo \
  --component execution-status

dream req analyze --case <case_id>
dream req impact --case <case_id>
dream req questions --case <case_id> --role TL
dream req brief --case <case_id> --llm-provider openai-compatible
dream req jira --case <case_id> --llm-provider openai-compatible
```

Expected demo outputs:

- `artifacts/requirement-cases/<case_id>/engineering-brief.md`
- `artifacts/requirement-cases/<case_id>/jira-draft.md`

### 3.4 PR Review Assistant

DREAM reviews a local PR diff and optional Jira-style context.

It uses:

- changed file parsing
- added/removed line counts
- rough changed content
- knowledge pack retrieval
- codebase memory retrieval
- related tests
- historical docs when available

Demo command:

```bash
dream review pr \
  --team demo_team \
  --repo dfp-demo-repo \
  --diff examples/pr-diffs/DFP-109-execution-monitor-auto-refresh.diff \
  --jira knowledge_packs/demo_team/docs/historical-jira/DFP-109-execution-monitor-auto-refresh.md \
  --llm-provider openai-compatible
```

Expected demo output:

- `artifacts/pr-review-summary-<run_id>.md`

The PR review does not approve, reject, merge, block, or post real PR comments.
It is a human review aid.

### 3.5 Evaluation Agent

DREAM evaluates generated outputs using deterministic scorecards.

Eval dimensions include:

- completeness
- evidence quality
- impact accuracy
- role coverage
- test awareness
- historical context
- actionability
- specificity
- hallucination risk

Demo commands:

```bash
dream eval run \
  --target-type engineering_brief \
  --case <case_id> \
  --team demo_team \
  --profile async-status-tracking

dream eval run \
  --target-type pr_review \
  --run <pr_review_run_id> \
  --team demo_team \
  --profile async-status-tracking
```

Expected demo outputs:

- `artifacts/evals/<evaluation_id>.md`
- `artifacts/evals/<evaluation_id>.json`

### 3.6 Audit Trail

Every major workflow writes an audit record to SQLite.

Audit captures:

- run id
- timestamp
- use case
- team id
- case id or repo name when relevant
- input hash
- retrieved source paths
- model provider
- model name
- output path
- status
- warnings

Demo command:

```bash
dream audit list
dream audit show <run_id>
```

### 3.7 TestGen Plugin Interface

DREAM intentionally does not implement a full unit-test generation engine.

It provides:

- `TestGenProvider`
- `MockTestGenProvider`
- `JTestGenAdapter` stub

This keeps DREAM focused on the platform layer. JTestGen or another external
test-generation engine can be connected later.

## 4. High-Level Architecture

```text
User / Demo Operator
        |
        v
CLI / FastAPI
        |
        v
Workflow Services
  - Knowledge search
  - Codebase indexing/search
  - Requirement Case service
  - PR Review assistant
  - TestGen provider interface
  - Evaluation agent
        |
        v
Platform Services
  - Path safety
  - Config
  - LLM provider abstraction
  - Audit logger
        |
        v
Storage
  - Markdown knowledge packs
  - JSON codebase indexes
  - SQLite audit/eval/case data
  - Markdown/JSON artifacts
```

## 5. Component HLD

### CLI and API Layer

- Typer CLI exposes demo-friendly commands.
- FastAPI exposes workflow endpoints.
- Both call the same Python services.

Key modules:

- `dream/cli/main.py`
- `dream/api/routes.py`

### Knowledge Layer

- Loads `team.yaml`.
- Loads Markdown docs.
- Splits docs into chunks.
- Runs deterministic keyword retrieval.

Key modules:

- `dream/knowledge/pack_loader.py`
- `dream/knowledge/markdown_loader.py`
- `dream/knowledge/chunker.py`
- `dream/knowledge/retriever.py`

### Codebase Memory Layer

- Scans local repo files.
- Extracts Java/Python/TypeScript symbols.
- Builds concepts and source-to-test mappings.
- Writes JSON index artifacts.

Key modules:

- `dream/codebase/scanner.py`
- `dream/codebase/indexer.py`
- `dream/codebase/retriever.py`
- `dream/codebase/repository.py`

### Engineering Memory Retriever

Combines knowledge retrieval and codebase retrieval into a structured evidence
list for requirement analysis and PR review.

It now uses:

- query expansion for status/execution requests
- filtered and unfiltered knowledge retrieval
- balanced evidence selection across docs, history, code, tests, and concepts

Key module:

- `dream/memory/retriever.py`

### Requirement Case Service

Owns the fuzzy-request-to-Jira workflow.

Steps:

1. Create case.
2. Retrieve context.
3. Generate impact map.
4. Generate role-specific questions.
5. Generate Engineering Brief.
6. Generate Jira Draft.
7. Log audit records.

OpenAI-compatible generation is opt-in for brief and Jira draft.

Key modules:

- `dream/requirement_cases/service.py`
- `dream/requirement_cases/impact.py`
- `dream/requirement_cases/questions.py`
- `dream/requirement_cases/brief.py`
- `dream/requirement_cases/jira.py`

### PR Review Assistant

Owns the diff-to-review workflow.

Steps:

1. Parse unified diff.
2. Retrieve knowledge context.
3. Retrieve codebase memory if repo index exists.
4. Identify related tests when possible.
5. Generate PR review summary.
6. Log audit record.

OpenAI-compatible generation is opt-in.

Key modules:

- `dream/review/diff_parser.py`
- `dream/review/pr_review.py`

### LLM Provider Layer

DREAM defaults to local deterministic/mock providers.

Supported:

- `MockLLMProvider`
- `OpenAICompatibleProvider`

OpenAI-compatible provider reads:

- `OPENAI_API_KEY`, or
- `OPENAI_COMPATIBLE_API_KEY`

Key modules:

- `dream/llm/base.py`
- `dream/llm/mock_provider.py`
- `dream/llm/openai_compatible.py`

### Audit and Eval Layer

Audit records generation runs.

Eval creates deterministic scorecards to catch missing evidence, missing tests,
missing role coverage, weak historical context, and hallucination risk.

Key modules:

- `dream/audit/logger.py`
- `dream/audit/repository.py`
- `dream/evals/evaluator.py`
- `dream/evals/evidence.py`
- `dream/evals/repository.py`

## 6. Main Demo Flow

### Step 1: Search team knowledge

```bash
dream kb search --team demo_team --query "execution status stuck running"
```

### Step 2: Index codebase memory

```bash
dream codebase index \
  --team demo_team \
  --repo examples/dfp-demo-repo \
  --name dfp-demo-repo
```

### Step 3: Create and analyze a Requirement Case

```bash
dream req create \
  --team demo_team \
  --request "Users say forecast jobs sometimes run for too long. The execution page should tell them which task is still running and refresh automatically, but the exact status labels and timeout behavior are not clear." \
  --role BA \
  --app ForecastDemo \
  --component execution-status

dream req analyze --case <case_id>
```

Expected talking point:

> DREAM did not just write a ticket. It built an evidence-backed requirement
> case using docs, code, tests, concepts, incidents, and historical delivery
> memory.

### Step 4: Review impact and TL questions

```bash
dream req impact --case <case_id>
dream req questions --case <case_id> --role TL
```

Expected talking point:

> DREAM identifies backend, API, frontend, workflow, test, and ops impact, then
> creates role-specific questions before implementation begins.

### Step 5: Generate Engineering Brief and Jira Draft

```bash
dream req brief --case <case_id> --llm-provider openai-compatible
dream req jira --case <case_id> --llm-provider openai-compatible
```

Expected talking point:

> The output is Jira-ready but not auto-approved. It is explicitly a draft for
> human review.

### Step 6: Evaluate generated outputs

```bash
dream eval run \
  --target-type engineering_brief \
  --case <case_id> \
  --team demo_team \
  --profile async-status-tracking

dream eval run \
  --target-type jira_draft \
  --case <case_id> \
  --team demo_team \
  --profile async-status-tracking
```

Expected talking point:

> DREAM has a quality gate. It can say the output is useful but still needs
> human review because specific tests or historical references are missing.

### Step 7: Pretend a PR was created

```bash
dream review pr \
  --team demo_team \
  --repo dfp-demo-repo \
  --diff examples/pr-diffs/DFP-109-execution-monitor-auto-refresh.diff \
  --jira knowledge_packs/demo_team/docs/historical-jira/DFP-109-execution-monitor-auto-refresh.md \
  --llm-provider openai-compatible
```

Expected talking point:

> DREAM reviews the PR diff, connects it to Jira context and codebase memory,
> and creates a reviewer aid. It does not approve, reject, merge, or post to a
> real PR.

### Step 8: Audit review

```bash
dream audit list
dream audit show <run_id>
```

Expected talking point:

> Every run is traceable: input hash, sources used, model provider, output path,
> status, and warnings.

## 7. Demo Success Criteria

The demo is successful when it shows:

- vague request becomes structured Jira draft
- codebase memory is used
- historical incidents/Jira/PRs influence the output
- role-specific questions are generated
- PR review summary is generated from a diff
- output is audited
- output is evaluated
- no real enterprise data is used
- no real Jira/GitHub side effect occurs

## 8. Guardrails

DREAM's MVP guardrails:

- mock provider by default
- OpenAI-compatible provider is opt-in
- no external API required for tests
- path traversal protection for file inputs
- local SQLite audit/eval storage
- local artifact outputs
- synthetic DemoCorp data only
- no real Jira integration
- no real GitHub PR posting
- no production TestGen engine

## 9. Current Limitations

This is demo-ready, not production-integrated.

Known limitations:

- no real Jira ticket creation
- no real GitHub PR commenting
- no vector database
- no full code graph
- no auth/multi-tenant deployment
- OpenAI output quality depends on retrieved evidence
- Eval scorecards may be strict because golden profiles expect specific files,
  incidents, Jira stories, and PRs

## 10. Recommended Demo Positioning

Use this phrasing:

> DREAM is a codebase-aware engineering memory platform. It helps teams turn
> ambiguous business requests and PR diffs into evidence-backed engineering
> artifacts for human review.

Avoid this phrasing:

> DREAM automatically writes final Jira tickets and approves PRs.

The correct positioning is:

> DREAM produces reviewable drafts, reviewer questions, impact maps, PR review
> aids, audit records, and eval scorecards. Human review remains required.
