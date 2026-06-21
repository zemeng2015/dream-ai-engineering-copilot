<!-- SPDX-License-Identifier: Apache-2.0 -->

# Demo Dataset: DemoCorp Forecast Platform

DFP is a synthetic enterprise forecast and analytics product used to demonstrate DREAM as a codebase-aware engineering memory platform.

## Core Objects
Job, Workflow, Task, Execution, and OutputArtifact.

## Architecture Layers
UI, Java backend, AWS-style orchestration, and Python processors.

## User Roles
Analyst, Operator, Admin, BA, TL, FE, BE, QA, and OPS.

## Folder Structure
The dataset includes domain docs, architecture docs, runbooks, incidents, historical Jira, historical PRs, testing docs, PR review docs, concept memory, fake code, fake diffs, rough requests, and example outputs.

## Requirement Intelligence
Use `examples/requirement-requests` to create Requirement Cases and retrieve evidence from docs and codebase memory.

## PR Review
Use `examples/pr-diffs` with historical Jira docs to review DFP changes with codebase memory.

## Codebase Memory
Index `examples/dfp-demo-repo` and search for `status tracker`, `duplicate output`, `partial success`, `Athena preview`, or `task config validation`.
