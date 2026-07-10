<!-- SPDX-License-Identifier: Apache-2.0 -->

# Pilot Security Foundation

Status: implemented and tested on `codex/pilot-security-foundation`; this is a
public-core security contract, not approval to ingest organization data.

## Security Invariants

- `public-demo` accepts only `public_demo / local_demo` resources.
- `private-extension` requires a named authenticated principal, explicit team
  membership, an allowed action role, a versioned source ACL, and a matching
  principal or group.
- Missing identity, team, role, ACL scope, ACL version, or ACL subject fails
  closed.
- `security_admin` does not bypass source ACLs.
- Unmarked API routes are automatically disabled in private mode.
- Only `/health/live` is anonymous; it returns `{"status":"ok"}` and no runtime,
  provider, model, source, or configuration details.
- FastAPI `/docs`, `/redoc`, and `/openapi.json` metadata endpoints are disabled
  in private mode.
- Local file-path PR inputs are disabled in private mode.
- Access metadata propagates through documents/chunks, code indexes/files/
  symbols/concepts/tests, graph nodes, MemoryClaims, Requirement evidence,
  Context Trails/Packs, prompt previews, and PR artifacts.
- Derived Case/PR artifacts receive an ACL no broader than every source actually
  used. The creating principal is retained, while groups are limited to the
  intersection of the requested workspace ACL and source ACLs.
- Derived artifacts retain every underlying `source_acl_version`. A persistent,
  team-scoped revocation ledger denies both the original source and every
  derived artifact on the next policy decision.

## Signed Identity Boundary

Private API routes do not trust plain caller headers. An approved authentication
proxy must sign this canonical payload with HMAC-SHA256:

```text
principal_id
sorted,comma-separated team_ids
sorted,comma-separated group_ids
sorted,comma-separated roles
unix_timestamp
request_id
uppercase HTTP method
request path
```

Required headers:

```text
X-DREAM-Principal-Id
X-DREAM-Team-Ids
X-DREAM-Roles
X-DREAM-Identity-Timestamp
X-DREAM-Identity-Signature
X-Request-Id
```

Optional headers are `X-DREAM-Group-Ids` and `X-DREAM-Identity-Key-Id`.
Wildcard teams are forbidden. The signature is bound to request id, method, and
path, so it cannot be replayed against another route. The default replay window
is 60 seconds and can only be configured between 10 and 300 seconds.

Deployment configuration must come from the approved secret manager:

```powershell
$env:DREAM_CONFIG_FILE = 'C:\approved-private\dream.yaml'
$env:DREAM_IDENTITY_HEADER_SECRET = '<at-least-32-byte-secret>'
$env:DREAM_IDENTITY_HEADER_KEY_ID = 'pilot-key-2026-01'
$env:DREAM_IDENTITY_MAX_CLOCK_SKEW_SECONDS = '60'
```

The HMAC contract authenticates the proxy assertion; it does not replace
enterprise SSO. The proxy must authenticate through the organization-approved
OIDC/SAML mechanism, strip all inbound DREAM identity headers, map current group
and team membership, sign fresh assertions, and prevent direct network access to
the DREAM API.

## Private API Surface

ACL-enforced private routes currently cover:

- bounded PR Review;
- codebase search, concepts, file listing, and authorized file content;
- graph search, explain, and neighbors;
- Context Trail, Context Pack, prompt preview, and memory report;
- approved MemoryClaim search and context card; and
- Requirement Case create/analyze/read, impacts, questions, human decisions,
  brief, Jira draft/context, and readiness.

The private guard intentionally blocks codebase/graph build, Knowledge Intake,
Memory scan/review/conflict administration, TestGen, Audit/Eval administration,
legacy requirement draft, Qwen showcase, and all other unmarked routes. Those
surfaces remain available in `public-demo`; they must receive action-specific
authorization, connector ACL propagation, and negative tests before being
enabled in `private-extension`.

## Verified Negative Cases

Automated tests prove:

- unsigned, expired, tampered, wildcard-team, and wrong-key assertions fail;
- missing identity configuration fails closed;
- cross-team and cross-group Requirement Cases are hidden;
- denied chunks, code files, graph nodes, graph neighbors, graph paths, and
  MemoryClaims are excluded;
- denied source names and content do not enter Requirement evidence, Jira
  output, prompt preview, or Context Trail; and
- a broad workspace ACL is narrowed when its selected sources have a narrower
  ACL; and
- revoking a source ACL version invalidates both source retrieval and a derived
  Case/PR artifact carrying that lineage.

Run the focused security suite:

```powershell
python -m pytest `
  tests/test_access_policy.py `
  tests/test_signed_proxy_identity.py `
  tests/test_api_private_security.py `
  tests/test_acl_aware_retrieval.py `
  tests/test_access_revocation.py `
  tests/test_private_requirement_acl_flow.py
```

## Still Required Before Real Sources

This foundation does not yet prove:

- organization-approved SSO/proxy deployment and network isolation;
- connector-side automatic ACL/revocation synchronization or identity/group
  lifecycle integration;
- deletion cascades for source bodies, indexes, prompts, caches, and artifacts;
- action-specific authorization for currently blocked administration routes;
- enterprise DLP/classification, private storage, retention/deletion, audit
  export, incident response, data residency, or provider approval; or
- Security/Data/source-owner approval of the exact Pilot data flow.

### Frontend Dependency Blocker

The 2026-07-10 clean install audit reports 7 production dependency findings
(6 high, 1 moderate) in the Angular 19.2.25 runtime family and 28 total findings
when build/test dependencies are included. npm currently offers remediation only
through an Angular 21 major upgrade. The current SPA does not configure Angular
SSR, hydration, `HttpTransferCache`, or direct `formatDate` usage, which limits
some listed exploit paths but does not close the dependency gate.

Do not run `npm audit fix --force` on the presentation branch. Perform the
Angular 21 migration as a separate reviewed product slice, rebuild/test the
exact bundle, rerun production and full audits, and obtain the normal enterprise
dependency approval or a time-bounded exception before a Pilot deployment.

`source_acl_version`, derived lineage, and the core revocation ledger enforce
fail-closed invalidation once a version is revoked. A connector must still feed
source-system revocations into that ledger and trigger required deletion
cascades. Until these items are approved and tested, real-source ingestion
remains **No-Go**.
