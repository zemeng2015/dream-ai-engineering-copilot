<!-- SPDX-License-Identifier: Apache-2.0 -->

# DOCX Intake Placeholder

This directory documents the intended DOCX intake path without committing a
binary `.docx` fixture. The next phase can add a parser-backed fixture when the
repository intentionally supports binary document extraction.

## Expected Synthetic Upload

```text
DemoCorp-Forecast-SLA-Policy.docx
```

Expected metadata:

```yaml
app: ForecastDemo
component: forecast-operations
doc_type: policy
source_system: local_upload
synthetic: true
```

## Parser Boundary

Until DOCX parsing is implemented, importing a `.docx` file should produce a
clear draft warning:

```text
DOCX parser is not configured. Upload a Markdown transcript or enable the
document parser before promotion.
```

The warning should not block the runbook or HLD demos. It should also prevent
the placeholder from being promoted into trusted retrieval context.

## Transcript Excerpt For Manual Testing

If a manual transcript is needed, use this synthetic text:

```text
DemoCorp Forecast SLA Policy

ForecastDemo operators should see stale execution warnings after two polling
intervals without status movement. Retry guidance should be visible only after
execution reaches a stable non-running state. Duplicate retry requests for the
same run id and workflow version should be treated as one operator intent.
```

Expected candidate claims:

- stale execution warnings appear after two polling intervals
- retry guidance is visible only for stable non-running executions
- duplicate retry requests for the same run id and workflow version represent
  one operator intent
