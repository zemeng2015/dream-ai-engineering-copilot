<!-- SPDX-License-Identifier: Apache-2.0 -->

# Audit and Eval

Every generation run writes an audit record to SQLite. The record includes run
id, timestamp, use case, team id, input hash, retrieved source paths, model
provider, model name, output path, status, and warnings.

Human ratings store usefulness, correctness, comments, and creation time. Ratings
help teams compare generated output quality without relying on private data in
the open-source demo.

## Automated Evaluation

The Evaluation Agent creates deterministic scorecards for Requirement Cases,
impact maps, role questions, engineering briefs, Jira drafts, PR review
summaries, TestGen reports, and general Markdown artifacts.

The default evaluator is rule-based. It checks required sections, source
coverage, evidence categories, role coverage, test awareness, historical
incident/Jira/PR context, actionability, specificity, and hallucination risk.
It does not call an external LLM.

Scorecards are written to `artifacts/evals/` and stored in SQLite. Evaluation
runs also create audit records with use case `evaluation_scorecard`.

Run an evaluation:

```bash
dream eval run \
  --target-type engineering_brief \
  --artifact examples/outputs/engineering-brief-async-status-example.md \
  --team demo_team \
  --profile async-status-tracking
```

List and inspect scorecards:

```bash
dream eval list
dream eval show <evaluation_id>
```

Human ratings remain separate from automated scorecards. The intended workflow is
to use automated evaluation for fast quality checks and human rating for reviewer
feedback after the artifact is used.

## Pilot Evidence Bundle

The offline `dream audit export-bundle` command creates a team-scoped,
metadata-only evidence snapshot spanning Audit/Eval, revocation, connector,
lineage, DLP and provider-egress records. `dream audit verify-bundle` checks the
fixed schema, exact file set, section hashes and optional independently retained
bundle root. Bundle v2 includes team-scoped successful identity and access-policy
decisions plus deployment-scoped identity rejection aggregates; legacy v1
verification remains supported. See
[Pilot Evidence Export Foundation](pilot-evidence-export-foundation.md) for
commands, snapshot semantics and limitations.
