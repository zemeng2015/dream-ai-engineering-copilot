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

## API and UI

The current FastAPI surface used by the Angular Codebase Index page is:

```text
POST /codebase/index
GET  /codebase/index?team_id=demo_team&repo_name=dfp-demo-repo
GET  /codebase/files?team_id=demo_team&repo_name=dfp-demo-repo
GET  /codebase/file-content?team_id=demo_team&repo_name=dfp-demo-repo&file_path=...
GET  /codebase/concepts?team_id=demo_team&repo_name=dfp-demo-repo
GET  /codebase/search?team_id=demo_team&repo_name=dfp-demo-repo&query=...
```

The `/codebase` frontend page is a repo browser plus saved index JSON inspector.
It shows:

- folder breadcrumb and file list from the saved repo JSON index
- selected file content read through FastAPI
- selected file JSON record, with the full repo index collapsed below it
- evidence search results
- an impact map that groups concepts by affected file and test counts

The UI intentionally shows file names in dense lists and keeps full paths in
detail/hover surfaces where possible.

## Requirement Analysis

Requirement Case analysis searches both the team knowledge pack and any available
codebase index. This lets DREAM connect a rough request to docs, code files,
symbols, tests, and concepts before generating an engineering brief.

No vector database is required in Phase 2. Retrieval is deterministic keyword and
metadata matching.
