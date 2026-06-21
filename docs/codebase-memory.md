<!-- SPDX-License-Identifier: Apache-2.0 -->

# Codebase Memory

Codebase memory is DREAM's lightweight structured index of a local repository.
It is more than generic RAG because it records engineering structure: files,
roles, languages, symbols, endpoint-like methods, test mappings, dependencies,
concepts, summaries, and warnings.

## What It Stores

- Repo tree and file nodes
- Source, test, config, docs, and unknown file roles
- Java, Python, and TypeScript symbols
- Java controller/endpoint-like annotations where detectable
- Simple imports and source-to-test relationships
- Concept tags such as `job execution`, `status tracking`, and `batch job`
- JSON artifacts under `artifacts/codebase-indexes/{team_id}/{repo_name}.json`

## Run Indexing

```bash
dream codebase index \
  --team demo_team \
  --repo examples/java-demo-repo \
  --name java-demo-repo
```

Search:

```bash
dream codebase search \
  --team demo_team \
  --repo java-demo-repo \
  --query "async status tracking"
```

## Requirement Analysis

Requirement Case analysis searches both the team knowledge pack and any available
codebase index. This lets DREAM connect a rough request to docs, code files,
symbols, tests, and concepts before generating an engineering brief.

No vector database is required in Phase 2. Retrieval is deterministic keyword and
metadata matching.
