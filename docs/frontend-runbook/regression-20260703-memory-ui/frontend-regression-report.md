# DREAM Frontend Regression & Demo Runbook

Run date: 2026-07-03
Base URL: http://localhost:4300

> Historical report. The live FastAPI UI was simplified after this run. Treat
> this file as a record of the 2026-07-03 regression pass, not as the current
> product acceptance baseline. Regenerate runbook artifacts before a new UI
> review.

## Regression Summary

- `npm run build`: PASS
- `npx ng test --watch=false --browsers=ChromeHeadless`: PASS, 11 specs successful
- Browser route smoke test: PASS, 14 routes loaded
- Console warnings/errors: 0 on all checked routes
- Horizontal overflow: none on all checked routes
- Mobile spot check already performed for Memory Management at 390x844: PASS

## Page Function Guide

### 1. Mission Control

- Route: `/mission-control`
- Heading verified: `Review Dashboard`
- Regression status: `PASS`
- Screenshot: `screenshots/01-mission-control.png`
- Purpose: Review dashboard for memory inventory, source review queue, Jira draft review, PR review session, and approved outputs.
- Functional notes:
  - Shows high-level review metrics for memory docs, uploads, Jira drafts, PR reviews, and approved outputs.
  - Lists structured source documents waiting for review before memory promotion.
  - Separates Jira Draft Review and PR Review Session so product owners can validate each output stream independently.
  - Primary action: Upload Source; secondary actions route to intake, workbench, memory, trust, and context trail.
- Key visible actions: `Upload Source`, `Open intake`, `Review`, `Review`, `Open workbench`, `Open workbench`, `Advanced details`, `Memory Hub`

### 2. Memory Management

- Route: `/memory`
- Heading verified: `Memory Management`
- Regression status: `PASS`
- Screenshot: `screenshots/02-memory-management.png`
- Purpose: Operational memory management overview with memory counts, structured docs awaiting review, quick actions, memory domains, and advanced diagnostics links.
- Functional notes:
  - Provides a simplified memory operations dashboard without embedding advanced detail pages.
  - Shows approved memory card count, structured docs needing review, code memory files, and eval evidence health.
  - Keeps review queue focused on parsed structured docs awaiting human approval.
  - Routes deeper inspection to Knowledge Intake, Knowledge Memory, Codebase Memory, Trust Center, Retrieval Trace, and Context Trail.
- Key visible actions: `Search Memory`, `Upload Source`, `Open intake`, `Upload SourceAdd a runbook, doc, or HLD for parsing.`, `Review Structured DocsApprove parsed cards before promotion.`, `Search MemoryFind approved evidence by concept.`, `Open Code MemoryInspect indexed files and test coverage.`, `Open intake`

### 3. Engineering Workbench

- Route: `/workbench`
- Heading verified: `Engineering Workbench`
- Regression status: `PASS`
- Screenshot: `screenshots/03-engineering-workbench.png`
- Purpose: Entry point for Jira draft and PR review workflows.
- Functional notes:
  - Provides the main workflow switch between Jira Draft and PR Review sessions.
  - Jira Draft flow starts from a fuzzy business request and produces memory-backed impact, open questions, proposal, and eval status.
  - PR Review flow starts from Jira context and PR diff and produces related code/memory impact plus review guidance.
  - Advanced settings are collapsed to keep the first-use flow simple.
- Key visible actions: `Trust CenterOpen retrieval trail`, `Jira DraftBusiness request -> memory and impact -> open questions -> Jira proposal.`, `PR ReviewDiff and Jira context -> related code -> evidence-backed review aid.`, `Advanced settings`, `Generate Jira Proposal`

### 4. Knowledge Intake

- Route: `/knowledge-intake`
- Heading verified: `Knowledge Intake`
- Regression status: `PASS`
- Screenshot: `screenshots/04-knowledge-intake.png`
- Purpose: Upload, parse, review, approve, and promote source documents into memory cards.
- Functional notes:
  - Accepts source uploads such as runbooks, DOCX notes, and Confluence/HLD content.
  - Shows source processing state, reviewer, target pack, and proposed memory card count.
  - Lets reviewer re-parse, approve cards, and promote approved cards into a memory pack.
  - Displays proposed cards, retrieval tags, and reviewer notes for controlled memory promotion.
- Key visible actions: `Re-parse`, `Approve Cards`, `Promote Cards`, `stuck running`, `operator escalation`, `status tracker`, `processor completion`

### 5. Knowledge Memory

- Route: `/knowledge`
- Heading verified: `Knowledge Memory`
- Regression status: `PASS`
- Screenshot: `screenshots/05-knowledge-memory.png`
- Purpose: Search approved knowledge chunks by concept, app, component, and doc type.
- Functional notes:
  - Searches approved knowledge chunks by query and metadata filters.
  - Shows matched evidence chunks with source path, app, component, doc type, and concepts.
  - Supports user/developer inspection of what evidence can be retrieved for generation.
  - Purpose is evidence lookup, not upload or approval.
- Key visible actions: `status stuck running`, `status tracker`, `operator runbook`, `processor completion`, `knowledge_packs/demo_team/docs/incidents/INC-103-status-stuck-running.md`

### 6. Codebase Memory

- Route: `/codebase`
- Heading verified: `Memory Atlas`
- Regression status: `PASS`
- Screenshot: `screenshots/06-codebase-memory.png`
- Purpose: Inspect indexed code capability memory, trust status, affected files, tests, concepts, risks, and evidence links.
- Functional notes:
  - Shows capability-level memory from indexed source files and tests.
  - Displays trust state, owner, confidence, affected files, tests, docs, concepts, risks, and gaps.
  - Supports impact-map reasoning for Jira draft and PR review workflows.
  - Detailed code memory stays here instead of being duplicated in Memory Management.
- Key visible actions: `Collection PlanningNeeds Human Review`, `Competitor DiscoverySecurity Sensitive`, `Human Review GateWeak Evidence`, `Image OpsSecurity Sensitive`, `License and Billing GatesSecurity Sensitive`, `Supplier OutreachNo Owner`, `Ready4`, `Review1`

### 7. Retrieval Trace

- Route: `/graph`
- Heading verified: `Retrieval Paths`
- Regression status: `PASS`
- Screenshot: `screenshots/07-retrieval-trace.png`
- Purpose: Trace how business concepts expand into docs, incidents, code, tests, Jira, and PR evidence paths.
- Functional notes:
  - Explains how a concept expands across docs, incidents, code files, tests, Jira, and PR history.
  - Lets users inspect why selected sources were included before prompt assembly.
  - Provides prompt boundary notes so generated outputs remain evidence-backed.
  - Advanced diagnostic surface for developers and reviewers.
- Key visible actions: `Trace Sources`, `execution status`, `duplicate output`, `output preview`, `partial recovery`

### 8. Context Trail

- Route: `/context-intelligence`
- Heading verified: `Context Intelligence`
- Regression status: `PASS`
- Screenshot: `screenshots/08-context-trail.png`
- Purpose: Review retrieval trail, context pack sections, prompt preview, logic chain, and evidence cards.
- Functional notes:
  - Shows retrieval trail, context pack sections, prompt preview, logic chain, and evidence cards.
  - Validates whether enough relevant evidence was assembled for generation.
  - Helps developers debug context assembly and prompt slots.
  - Used by Trust Center and eval flows as supporting detail.

### 9. Trust Center

- Route: `/trust`
- Heading verified: `Trust Center`
- Regression status: `PASS`
- Screenshot: `screenshots/09-trust-center.png`
- Purpose: Audit context quality and eval evidence before generated outputs are used.
- Functional notes:
  - Consolidates context quality and audit-facing evidence surfaces.
  - Lets reviewers inspect retrieval trail and audit/eval status before trusting output.
  - Provides a governance checkpoint for generated Jira/PR content.
  - Advanced users can drill into context evidence and score details.

### 10. Jira Draft

- Route: `/requirements`
- Heading verified: `Jira Draft`
- Regression status: `PASS`
- Screenshot: `screenshots/10-jira-draft.png`
- Purpose: Input a fuzzy business request, inspect memory and impact, review eval feedback, answer open questions, and generate a Jira proposal.
- Functional notes:
  - Accepts fuzzy business requirements as input.
  - Shows selected memory logic and impact map with affected file counts and expandable details.
  - Keeps open questions editable for human clarification.
  - Generates a Jira proposal and shows Eval Agent judgment with link to audit detail.
- Key visible actions: `Advanced settings`, `Generate Jira Proposal`

### 11. PR Review

- Route: `/review`
- Heading verified: `PR Review`
- Regression status: `PASS`
- Screenshot: `screenshots/11-pr-review.png`
- Purpose: Input Jira context and PR diff, inspect memory/code impact and eval feedback, then generate a PR review summary.
- Functional notes:
  - Accepts Jira context and PR diff as input.
  - Shows Eval Agent opinion, memory/code impact, changed files, related code, and memory docs used.
  - Generates a PR review summary for human review before posting.
  - Detailed settings are collapsed to keep the main review flow focused.
- Key visible actions: `Advanced settings`, `Generate PR Review`

### 12. TestGen Stub

- Route: `/testgen`
- Heading verified: `TestGen Stub`
- Regression status: `PASS`
- Screenshot: `screenshots/12-testgen-stub.png`
- Purpose: Show the placeholder test-generation workflow and mock run report.
- Functional notes:
  - Shows mock test-generation workflow surface only.
  - Creates a stub plan/report without generating or modifying unit tests.
  - Clarifies that real JTestGen provider integration is out of scope for this UI demo.
  - Useful for future provider integration validation.
- Key visible actions: `Plan Stub`, `Run Safe Stub`

### 13. Eval Detail

- Route: `/audit`
- Heading verified: `Eval & Audit`
- Regression status: `PASS`
- Screenshot: `screenshots/13-eval-detail.png`
- Purpose: Inspect audit/evaluation detail for generated Jira draft or PR review outputs.
- Functional notes:
  - Displays generated-output evaluation detail.
  - Shows scorecard-style audit output and recommendations.
  - Used as the detail target from Jira Draft and PR Review Eval Agent panels.
  - Supports product validation of traceability and readiness.
- Key visible actions: `Save Human Rating`, `architectureDocs: yes`, `codeFiles: yes`, `conceptMemory: no`, `domainDocs: yes`, `historicalJira: yes`, `historicalPr: no`, `incidents: yes`

### 14. Settings

- Route: `/settings`
- Heading verified: `Settings`
- Regression status: `PASS`
- Screenshot: `screenshots/14-settings.png`
- Purpose: Review environment, mock mode, API health, and runtime configuration.
- Functional notes:
  - Shows runtime environment and mock mode status.
  - Displays API/base configuration and demo workspace context.
  - Used by developers to verify whether the UI is running against mock or API-backed mode.
  - Keeps environment details separate from user task flows.

## Acceptance Notes

- Memory Management no longer embeds Intake, Atlas, Trace, or Evidence Browser as full tabs.
- Detailed pages remain accessible by links instead of duplicated in the management page.
- Jira Draft and PR Review remain separate review sessions.
- Advanced diagnostic surfaces remain available but are not default-first user content.
