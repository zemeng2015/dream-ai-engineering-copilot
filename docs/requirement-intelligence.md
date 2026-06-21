<!-- SPDX-License-Identifier: Apache-2.0 -->

# Requirement Intelligence

DREAM's primary Phase 2 workflow is the Requirement Case. It is not a generic
chatbot and not just a Jira ticket generator. It turns a rough request into a
source-backed engineering analysis object.

## Workflow

1. Intake: create a case from a rough business request.
2. Context: retrieve relevant knowledge docs and codebase memory.
3. Impact Map: classify likely workflow, backend, API, data, test, ops, security, and frontend impact.
4. Questions: generate role-specific clarification questions for BA, TL, FE, BE, QA, and OPS.
5. Engineering Brief: produce a reusable implementation planning document.
6. Jira Draft: produce a human-reviewable story draft.
7. Audit: record each generation step in SQLite.

## CLI Example

```bash
dream req create \
  --team demo_team \
  --request "Add async status tracking for long-running job execution" \
  --role BA

dream req analyze --case <case_id>
dream req impact --case <case_id>
dream req questions --case <case_id> --role TL
dream req brief --case <case_id>
dream req jira --case <case_id>
```

## Human Review

Generated briefs and Jira drafts are evidence-backed drafts. DREAM clearly
surfaces uncertainty and open questions so humans can confirm scope, behavior,
ownership, and test expectations before implementation.
