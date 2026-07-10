<!-- SPDX-License-Identifier: Apache-2.0 -->

# Controlled Enterprise Pilot Proposal

This is the leadership-ready proposal template for DREAM. Organization, team,
application, and owner names must be filled in only in the approved private
Pilot package; this public document contains no company data.

## Decision Requested

Authorize a six-week discovery Pilot to test whether governed engineering
context improves the quality and reviewability of early requirement decisions
for one team and one application, without enabling autonomous delivery actions.

The requested decision is approval to complete security/design review and run a
bounded Pilot—not approval for production rollout.

## Scope

| Item | Pilot boundary |
|---|---|
| Team | One sponsor engineering team |
| Application | One non-critical application/workflow |
| Repository | One explicitly allowlisted repository |
| Sources | Small SME-approved read-only set of architecture, runbook, testing, and historical records |
| Workflow | Rough request -> Requirement Case -> impact/questions -> human-gated draft -> proof/eval |
| Users | Named BA, TL, QA and Pilot operator/reviewer cohort |
| Writes | None to Jira, GitHub, deployment systems, email, or messaging |
| Model | One organization-approved endpoint/model configuration |
| Deployment | Approved private boundary and region |

PR Review may be evaluated as a secondary reuse case after the Requirement Case
workflow passes its trust gates. It is not required for the first Pilot success
decision.

## Owners

| Role | Responsibility |
|---|---|
| Executive sponsor | Approves scope, resolves organizational blockers, receives decision report |
| Product/Pilot owner | Defines workflow, adoption plan, and success decision |
| Technical owner | Operates DREAM, owns releases, incident response, and deletion |
| Security/Data owner | Approves data flow, provider, ACL, redaction, retention, and exceptions |
| Source owner | Approves exact repositories/documents and read-only access |
| SME reviewers | Create golden sets and rate correctness/usefulness |
| Independent evaluator | Reviews metrics, unsupported claims, and failure cases |

Named individuals must be assigned before real-source access.

## Six-Week Timeline

### Week 0 — Approval and Design Gate

- confirm sponsor, owners, scope, and exit criteria;
- complete threat model/data-flow review;
- approve provider, region, storage, retention, and source list; and
- prove that all external write paths remain disabled.

### Week 1 — Private Environment

- deploy inside the approved boundary;
- configure identity, least-privilege read access, logging, and deletion;
- ingest a tiny non-sensitive validation corpus; and
- pass access-denial, redaction, provenance, and audit smoke tests.

### Week 2 — Golden Baseline

- select 10–20 representative historical rough requests;
- have SMEs record expected impacts, critical questions, tests, history, and an
  acceptable first draft;
- record current manual cycle time and edit effort; and
- freeze the baseline before viewing DREAM output.

### Weeks 3–4 — Shadow Evaluation

- run DREAM read-only in parallel with the normal process;
- require human review and record every correction;
- investigate invalid citations, missing critical items, and access failures;
- make only reviewed, reversible changes to retrieval/policy; and
- do not use output for delivery unless the normal process independently accepts it.

### Week 5 — Controlled User Trial

- allow the named cohort to use DREAM for first-draft assistance;
- keep the existing approval and delivery process unchanged;
- measure usefulness, correctness, edit distance, latency, and reliability; and
- collect workflow friction and training feedback.

### Week 6 — Independent Review and Decision

- compare results with the frozen SME/manual baseline;
- review all trust/security incidents and exclusions;
- document limitations and operating cost; and
- decide: stop, extend under a new approval, or design a production phase.

## Success Metrics

All thresholds must be agreed before Week 2. Recommended measures are:

| Measure | Method |
|---|---|
| Impact recall | DREAM impacts matched against SME golden impacts |
| Critical-question recall | Required BA/TL/QA/OPS questions found before implementation |
| Citation validity | Selected citations resolve to allowed sources and support the statement |
| Unsupported claims | Organization-specific statements without valid support |
| Test/history coverage | Golden tests, incidents, Jira, and PR evidence recovered |
| Human edit distance | Difference between generated contract output and accepted SME draft |
| First-draft time | Same start/end definition for manual baseline and Pilot |
| Usefulness/correctness | Role-separated 1–5 rating plus correction notes |
| Reliability | Successful runs, parse failures, latency distribution, provider errors |
| Cost | Versioned provider usage plus Pilot infrastructure/operation effort |
| Data boundary | Unauthorized source access, leakage, external writes; target is zero |

Report distributions and failure cases, not only averages. Synthetic DFP and
competition results may explain the hypothesis but do not count as Pilot ROI.

## Proposed Decision Gates

The Pilot is successful only if:

- there are zero unauthorized source disclosures and zero external writes;
- citation validity and unsupported-claim thresholds are met;
- no critical risk/question category regresses materially versus baseline;
- the named SMEs judge the workflow useful enough to continue; and
- operational cost and latency fit the agreed next-phase envelope.

Failure of a security/data-boundary gate stops the Pilot. Quality shortfalls may
justify one time-bounded remediation cycle only if the sponsor and owners agree.

## Out of Scope

- production rollout or broad organization access;
- autonomous agents or automatic task execution;
- automatic Jira/PR creation, comments, approvals, merges, or deployment;
- general chat over enterprise data;
- broad connector rollout;
- Vector DB or complex graph-platform replacement;
- employee performance monitoring; and
- claims of labor reduction or ROI before controlled evidence exists.

## Leadership Ask

Approve the bounded six-week discovery Pilot and assign:

1. one executive sponsor;
2. one sponsor team/application/repository;
3. technical, Security/Data, source, and SME owners;
4. time for the Week 0 design review and Week 2 baseline; and
5. an explicit Week 6 stop/extend/advance decision meeting.

If these owners or gates cannot be assigned, keep DREAM at synthetic leadership
demo status and do not connect real organization data.
