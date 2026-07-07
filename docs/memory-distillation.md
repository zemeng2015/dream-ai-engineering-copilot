<!-- SPDX-License-Identifier: Apache-2.0 -->

# Governed Memory Distillation

DREAM memory distillation turns engineering evidence into reviewable memory
claims. It is intentionally narrower than generic RAG or automatic long-term
agent memory.

The MVP contract is:

```text
repo + docs + runbooks + incidents + PR/ticket-like history
  -> source records
  -> source spans
  -> deterministic RepoGraph/codebase facts
  -> semantic candidate claims
  -> validation gates
  -> reviewable memory diff
  -> durable memory ledger
  -> approved memory retrieval
```

Generated artifacts are views over source-backed memory. They are not treated as
authoritative evidence unless they point back to original sources.

## What Exists Now

The first implementation adds:

- `SourceRecord` and `SourceSpan` models
- `MemoryClaimV0`-style claim models
- deterministic structural claims from the codebase index
- heuristic semantic candidate claims from team knowledge-pack Markdown
- deterministic `match_explanation` and `matched_terms` for claims derived from
  promoted intake documents
- source/citation/security validation summary
- repo provenance capture for commit SHA, dirty state, scanner version, and schema version
- redacted source previews for secret-like assignments and common token patterns
- reviewable memory diff output
- true scan diff against a previous scan when available
- durable review ledger for approve/reject/quarantine events
- approved-claim search and context-card output
- MVP eval guardrails
- CLI commands and FastAPI endpoints

Artifacts are written under:

```text
artifacts/memory-scans/{team_id}/{scan_id}.json
artifacts/memory-scans/{team_id}/latest.json
artifacts/memory-evals/{team_id}/{evaluation_id}.json
artifacts/memory-ledgers/{team_id}.json
```

## CLI

```bash
dream memory scan \
  --team demo_team \
  --repo examples/java-demo-repo \
  --name java-demo-repo

dream memory diff --team demo_team

dream memory review \
  --team demo_team \
  --claim <claim_id> \
  --status approved \
  --reviewer zack

dream memory search --team demo_team --query "execution status"

dream memory context --team demo_team --query "execution status"

dream memory eval --team demo_team
```

## API

```bash
curl -X POST http://localhost:8000/memory/scan \
  -H "Content-Type: application/json" \
  -d '{"team_id":"demo_team","repo_path":"examples/java-demo-repo","repo_name":"java-demo-repo"}'

curl "http://localhost:8000/memory/diff?team_id=demo_team"

curl "http://localhost:8000/memory/conflicts?team_id=demo_team"

curl -X POST http://localhost:8000/memory/conflicts/resolve \
  -H "Content-Type: application/json" \
  -d '{"team_id":"demo_team","conflict_id":"<conflict_id>","winning_claim_id":"<claim_id>","reviewer":"zack","reason":"Source A is authoritative."}'

curl "http://localhost:8000/memory/conflict-resolutions?team_id=demo_team"

curl -X POST http://localhost:8000/memory/review \
  -H "Content-Type: application/json" \
  -d '{"team_id":"demo_team","claim_id":"<claim_id>","status":"approved","reviewer":"zack"}'

curl "http://localhost:8000/memory/search?team_id=demo_team&query=execution%20status"

curl "http://localhost:8000/memory/context-card?team_id=demo_team&query=execution%20status"

curl -X POST http://localhost:8000/memory/eval \
  -H "Content-Type: application/json" \
  -d '{"team_id":"demo_team"}'
```

## Claim Governance

The MVP distinguishes deterministic structure from semantic memory:

| Claim family | Promotion policy |
| --- | --- |
| File exists / language / role | approved when deterministic |
| Symbol defined in file | approved when extracted from parser/indexer |
| Endpoint-like symbol | approved when direct annotation evidence exists |
| Source-to-test mapping | candidate unless high-confidence exact evidence exists |
| Concept documented by Markdown | candidate |
| Runbook / incident / decision memory | candidate |
| Sensitive or secret-like source | quarantined |

Semantic claims are never auto-promoted in this MVP. They must remain candidates
until a reviewer approves them.

Review events are appended to a durable ledger. The ledger records claim id,
scan id, previous status, new status, reviewer, reason, review timestamp,
reviewer signature, field-level governance diffs, a claim snapshot, and
raw risk/conflict signals plus reviewer-readable signal explanations. The latest
ledger event for a claim overrides the scan's original governance status during
approved-claim retrieval.

`/memory/conflicts` reports active single-value conflict pairs. The report keeps
both claims, effective review statuses, latest review events, evidence paths,
intake document ids, and a conflict explanation so reviewers can compare the raw
trace before approving durable memory. `/memory/conflicts/resolve` supports the
initial `approve_winner_reject_other` action and writes both normal review
events plus a dedicated conflict resolution ledger event.

## Provenance And Redaction

Every scan writes a `schema_version` and `provenance` block. The provenance block
captures the scanned repo path, containing Git root, current commit SHA, dirty
state for the scanned path, dirty path list, and scanner version.

`SourceRecord.commit_sha` is populated from the scan provenance when the source
is inside a Git worktree. Source hashes and excerpt hashes are computed from the
original content, but `SourceSpan.preview` is redacted before it is persisted.
The MVP redacts secret-like assignments, AWS access keys, JWT-like tokens, and
private-key headers.

## MVP Guardrails

`dream memory eval` checks:

- citation validity
- unsupported claim rate
- secret leakage count
- structural claim count
- semantic candidate claim count
- auto-promoted semantic claim count

Current pass criteria:

```text
citation_validity == 1.0
unsupported_claim_rate <= 0.03
secret_leakage_count == 0
auto_promoted_semantic_claims == 0
```

These guardrails map directly to the product thesis: extract less, cite
everything, validate before promotion, preserve review, and avoid feedback-loop
memory pollution.

## HLD

```text
Source Registry
  -> Source Spans
  -> RepoGraph / Codebase Index
  -> Candidate Claims
  -> Validation Gates
  -> Memory Diff Review
  -> Memory Ledger
  -> Evidence Retrieval
  -> Requirement / PR / Wiki / Eval Outputs
```

The current implementation covers the path through candidate claims, validation,
true diff, durable ledger, compact UI approval workflow, approved-claim
retrieval, context-card output, and eval artifacts. Richer semantic explanation
and direct workflow integration are the next natural steps.
