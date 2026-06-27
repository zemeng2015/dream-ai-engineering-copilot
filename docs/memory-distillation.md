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
  -> durable memory ledger later
```

Generated artifacts are views over source-backed memory. They are not treated as
authoritative evidence unless they point back to original sources.

## What Exists Now

The first implementation adds:

- `SourceRecord` and `SourceSpan` models
- `MemoryClaimV0`-style claim models
- deterministic structural claims from the codebase index
- heuristic semantic candidate claims from team knowledge-pack Markdown
- source/citation/security validation summary
- repo provenance capture for commit SHA, dirty state, scanner version, and schema version
- redacted source previews for secret-like assignments and common token patterns
- reviewable memory diff output
- MVP eval guardrails
- CLI commands and FastAPI endpoints

Artifacts are written under:

```text
artifacts/memory-scans/{team_id}/{scan_id}.json
artifacts/memory-scans/{team_id}/latest.json
artifacts/memory-evals/{team_id}/{evaluation_id}.json
```

## CLI

```bash
dream memory scan \
  --team demo_team \
  --repo examples/java-demo-repo \
  --name java-demo-repo

dream memory diff --team demo_team

dream memory eval --team demo_team
```

## API

```bash
curl -X POST http://localhost:8000/memory/scan \
  -H "Content-Type: application/json" \
  -d '{"team_id":"demo_team","repo_path":"examples/java-demo-repo","repo_name":"java-demo-repo"}'

curl "http://localhost:8000/memory/diff?team_id=demo_team"

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
diff, and eval artifacts. The durable review ledger and UI approval workflow are
the next natural step.
