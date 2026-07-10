<!-- SPDX-License-Identifier: Apache-2.0 -->

# DLP Enforcement Foundation

Status: implemented and adversarially tested in the public core. This is a
deterministic engineering foundation, not an enterprise DLP product or approval
to ingest organization data.

## Enforced Text Boundaries

The `dream-dlp-v1` policy is applied at these boundaries:

- `pre_index`: Markdown knowledge loading, Knowledge Intake parsing, and
  codebase indexing;
- `pre_persist`: Requirement Case raw requests and later human answers/waiver
  reasons before SQLite or audit persistence;
- `pre_prompt`: all built-in LLM providers before a prompt reaches the delegate,
  plus saved Context/Jira prompt previews; and
- `post_response`: model text before it returns to a workflow.

The provider wrapper preserves the configured provider/model identity while
forwarding only the sanitized prompt. A blocking decision prevents the delegate
from being called.

## Versioned Rules

`dream-dlp-v1` deterministically:

- blocks PEM private keys;
- blocks common instruction-override phrases on input boundaries;
- blocks resources explicitly classified as `blocked`;
- blocks text larger than the configured inspection limit;
- redacts secret assignments, AWS access keys, JWTs, US SSNs, and email
  addresses.

Blocked source files remain visible as metadata-only file nodes with
classification `blocked`, but produce no symbols, concepts, or test mappings.
Blocked Knowledge Intake content is quarantined and produces no draft.
Redacted derived Markdown, indexes, cases, prompts, and model responses contain
typed placeholders rather than the matched value.

## Metadata-Only Evidence

Decisions append to `artifacts/pilot-security/dlp-events.jsonl`. The ledger
contains policy/stage/status, counts, categories, one-way fingerprints, content
hashes, and a hashed resource identifier. It does not persist the matched value,
raw resource path, prompt, source body, or model response.

The local JSONL ledger uses a process lock and strict schema validation. A Pilot
deployment needs a shared transactional/append-only evidence store with approved
retention, encryption, access, export, and monitoring controls.

## Adversarial Verification

Run the focused corpus and workflow tests:

```powershell
python -m pytest -q `
  tests/test_dlp_enforcement.py `
  tests/test_dlp_workflow_boundaries.py
```

The tests prove that representative secrets and PII do not enter derived
knowledge/index/case artifacts or the DLP ledger, critical content blocks before
model invocation or persistence, and blocked source content is quarantined or
excluded from indexing.

## Explicit Limitations

This foundation does not yet provide:

- an organization-approved classification taxonomy or policy owner;
- document-format-aware inspection for PDF, Office, images, OCR, archives, or
  arbitrary binary files;
- malware scanning, content-disarm/reconstruction, or encrypted-file handling;
- contextual ML/entity detection, allowlists, exception approval, or a
  false-positive operations process;
- connector-side scanning before the raw source copy enters approved private
  storage;
- a shared multi-instance policy/ledger service, SIEM export, alerting, or
  incident-response integration; or
- approved private storage, provider, network, residency, retention, deletion,
  or legal/privacy controls.

Raw Knowledge Intake uploads are retained as source copies so provenance and
human review remain possible. In a real Pilot those copies must live inside the
approved private ingestion/storage boundary; the public local artifact folder
is not that boundary.

Real-source ingestion therefore remains **No-Go** until Security, Data/Privacy,
the source owner, and the Pilot technical owner approve the complete data flow
and operating controls.
