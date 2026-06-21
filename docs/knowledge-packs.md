<!-- SPDX-License-Identifier: Apache-2.0 -->

# Knowledge Packs

A team knowledge pack lives under `knowledge_packs/<team_id>/`.

## team.yaml

`team.yaml` declares the team name, team id, applications, repositories, document
paths, review rules, requirement template, and test-generation rules.

## Markdown Docs

Markdown files are loaded from configured document paths. The first `#` heading
becomes the document title.

## Metadata

Markdown files can include front matter:

```yaml
---
app: BatchJobDemo
component: job-execution
doc_type: domain
---
```

The retriever can filter by `team_id`, `app`, `component`, and `doc_type`.

## Adding a New Team

Create a new directory under `knowledge_packs/`, add `team.yaml`, add Markdown
docs, and run `dream kb list-teams` plus `dream kb search` to verify retrieval.

