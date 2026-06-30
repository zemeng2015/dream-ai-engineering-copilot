<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Synthetic DemoCorp Confluence-style export. This is a local file, not a connector. -->

# DemoCorp Forecast Orchestration HLD

<metadata>
  <space>DFP</space>
  <page>Forecast Orchestration HLD</page>
  <app>ForecastDemo</app>
  <component>forecast-orchestration</component>
  <doc_type>architecture</doc_type>
  <synthetic>true</synthetic>
</metadata>

## Overview

ForecastDemo orchestrates long-running forecast jobs for DemoCorp planning
teams. The system accepts a job request, expands it into workflow tasks, tracks
execution status, materializes outputs, and exposes operator actions in the
console.

This file is formatted like an exported HLD so the intake pipeline can exercise
HTML-like blocks, tables, headings, and architecture metadata without calling a
real Confluence API.

## Component Responsibilities

<table>
  <tr>
    <th>Component</th>
    <th>Responsibility</th>
    <th>Intake Tags</th>
  </tr>
  <tr>
    <td>Job API</td>
    <td>Accept job requests and return execution ids.</td>
    <td>api, execution</td>
  </tr>
  <tr>
    <td>Workflow Service</td>
    <td>Create task plans and advance workflow versions.</td>
    <td>workflow, versioning</td>
  </tr>
  <tr>
    <td>Status Tracker</td>
    <td>Persist task and execution status for operator polling.</td>
    <td>status, polling</td>
  </tr>
  <tr>
    <td>Output Collector</td>
    <td>Materialize output records and enforce retry idempotency.</td>
    <td>output, reconciliation, idempotency</td>
  </tr>
  <tr>
    <td>Operator Console</td>
    <td>Display status, warnings, and allowed operator actions.</td>
    <td>frontend, operations</td>
  </tr>
</table>

## Data Flow

```text
Job Request
  -> Job API
  -> Workflow Service
  -> Task Execution
  -> Status Tracker
  -> Output Collector
  -> Operator Console
```

Status Tracker is the source for execution state shown to operators. Output
Collector is the owner for output materialization and duplicate retry
prevention. Operator Console should disable actions that are not valid for the
current execution state.

## Retry And Reconciliation Design Notes

- Retry requests should include run id, workflow version, requesting operator,
  and operator note.
- Output Collector should use run id plus workflow version as the idempotency
  key for reconciliation retry.
- The console should explain why retry is unavailable when execution status is
  `RUNNING`.
- The system should record whether retry was requested by an operator or by a
  scheduled recovery job.

## Non-Goals

- The POC does not implement a live Confluence connector.
- The POC does not send real operator notifications.
- The POC does not migrate historical DemoCorp documents.
- The POC does not modify non-demo data.

## Acceptance Notes For Intake

The intake pipeline should propose an architecture draft with:

- app: `ForecastDemo`
- component: `forecast-orchestration`
- doc type: `architecture`
- concepts: execution status, workflow versioning, output reconciliation,
  idempotent retry, operator action gating
- candidate claim: Output Collector owns retry idempotency for reconciliation
- candidate claim: Operator Console should disable invalid actions based on
  Status Tracker state
