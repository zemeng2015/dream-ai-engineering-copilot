// SPDX-License-Identifier: Apache-2.0

import { Injectable, computed, signal } from '@angular/core';

import {
  AuditRun,
  CodebaseFile,
  ContextEvidence,
  ContextIntelligenceSnapshot,
  EvaluationDimension,
  EvaluationScorecard,
  EvidenceGraphNode,
  EvidenceGraphPath,
  HumanRating,
  ImpactItem,
  KnowledgeChunk,
  KnowledgeIntakeItem,
  KnowledgePack,
  PrReviewInput,
  PrReviewResult,
  RequirementCase,
  RequirementDraftInput,
  RequirementDraftResult,
  TestGenStubInput,
  TestGenStubPlan,
  TestGenStubResult,
  WorkflowType,
} from './dream-models';

@Injectable({ providedIn: 'root' })
export class MockDreamService {
  private readonly auditRunsState = signal<AuditRun[]>(MOCK_AUDIT_RUNS);
  private readonly ratingsState = signal<HumanRating[]>(MOCK_RATINGS);
  private readonly requirementCasesState = signal<RequirementCase[]>(MOCK_REQUIREMENT_CASES);
  private readonly scorecardsState = signal<EvaluationScorecard[]>(MOCK_SCORECARDS);

  readonly auditRuns = this.auditRunsState.asReadonly();
  readonly ratings = this.ratingsState.asReadonly();
  readonly requirementCases = this.requirementCasesState.asReadonly();
  readonly scorecards = this.scorecardsState.asReadonly();
  readonly recentRuns = computed(() => this.auditRunsState().slice(0, 6));

  readonly health = {
    status: 'ok',
    mode: 'mock',
    apiBaseUrl: 'http://127.0.0.1:8000',
    note: 'The Angular demo uses local DFP mock data until API integration is enabled.',
  };

  listTeams(): string[] {
    return ['demo_team'];
  }

  listApps(): string[] {
    return ['ForecastDemo', 'BatchJobDemo', 'OutputPreviewDemo'];
  }

  listDocTypes(): string[] {
    return [
      'domain',
      'architecture',
      'runbooks',
      'incidents',
      'historical-jira',
      'historical-pr',
      'testing',
      'pr-review',
      'concepts',
    ];
  }

  listKnowledgePacks(): KnowledgePack[] {
    return MOCK_PACKS;
  }

  listKnowledgeChunks(): KnowledgeChunk[] {
    return MOCK_CHUNKS;
  }

  listKnowledgeIntakeQueue(): KnowledgeIntakeItem[] {
    return MOCK_KNOWLEDGE_INTAKE_QUEUE.map(cloneKnowledgeIntakeItem);
  }

  getContextIntelligenceSnapshot(): ContextIntelligenceSnapshot {
    return cloneContextIntelligenceSnapshot(MOCK_CONTEXT_INTELLIGENCE);
  }

  listCodebaseFiles(): CodebaseFile[] {
    return MOCK_CODEBASE_FILES;
  }

  listEvidenceGraphNodes(): EvidenceGraphNode[] {
    return MOCK_GRAPH_NODES;
  }

  searchEvidenceGraph(params: { query: string; topK?: number }): EvidenceGraphPath[] {
    const terms = tokenize(params.query);
    const topK = params.topK ?? 8;
    return MOCK_GRAPH_PATHS.map((path) => ({
      path,
      score: scoreSearchText(
        `${path.concept} ${path.path.join(' ')} ${path.risk} ${path.reviewHint}`,
        terms,
      ),
    }))
      .filter((item) => item.score > 0 || terms.length === 0)
      .sort((a, b) => b.score - a.score || a.path.concept.localeCompare(b.path.concept))
      .slice(0, topK)
      .map((item) => item.path);
  }

  searchKnowledge(params: {
    query: string;
    app?: string;
    component?: string;
    docType?: string;
    topK?: number;
  }): KnowledgeChunk[] {
    const terms = tokenize(params.query);
    const topK = params.topK ?? 5;
    return MOCK_CHUNKS.filter((chunk) => {
      const appMatch = !params.app || chunk.metadata.app === params.app;
      const componentMatch = !params.component || chunk.metadata.component === params.component;
      const docTypeMatch = !params.docType || chunk.metadata.docType === params.docType;
      return appMatch && componentMatch && docTypeMatch;
    })
      .map((chunk) => ({ chunk, score: scoreSearchText(searchTextForChunk(chunk), terms) }))
      .filter((item) => item.score > 0 || terms.length === 0)
      .sort((a, b) => b.score - a.score || a.chunk.title.localeCompare(b.chunk.title))
      .slice(0, topK)
      .map((item) => item.chunk);
  }

  searchCodebase(params: { query: string; topK?: number; layer?: string }): CodebaseFile[] {
    const terms = tokenize(params.query);
    const topK = params.topK ?? 8;
    return MOCK_CODEBASE_FILES.filter((file) => !params.layer || file.layer === params.layer)
      .map((file) => ({ file, score: scoreSearchText(searchTextForFile(file), terms) }))
      .filter((item) => item.score > 0 || terms.length === 0)
      .sort((a, b) => b.score - a.score || a.file.path.localeCompare(b.file.path))
      .slice(0, topK)
      .map((item) => item.file);
  }

  draftRequirement(input: RequirementDraftInput): RequirementDraftResult {
    const sources = this.searchKnowledge({
      query: input.roughBusinessRequest,
      app: input.app,
      component: input.component,
      topK: input.topK,
    });
    const codeEvidence = this.searchCodebase({ query: input.roughBusinessRequest, topK: 6 });
    const requirementCase = buildRequirementCase({
      rawRequest: input.roughBusinessRequest,
      role: input.role || 'BA',
      sources,
      codeEvidence,
    });
    this.requirementCasesState.update((cases) => [requirementCase, ...cases]);

    const scorecard = createScorecard({
      targetType: 'jira_draft',
      targetId: requirementCase.caseId,
      overallScore: 8.6,
      sourcePaths: [...sources.map((source) => source.sourcePath), ...codeEvidence.map((file) => file.path)],
      recommendations: [
        'Confirm task-level status labels with BA and FE before implementation.',
        'Add regression coverage for stuck RUNNING and PARTIAL_SUCCESS behavior.',
      ],
    });
    this.scorecardsState.update((cards) => [scorecard, ...cards]);

    const run = this.createRun('requirement_draft', input.teamId, input.app, 'success', sources, [
      ...codeEvidence.map((file) => file.path),
    ]);

    return {
      run,
      markdown: requirementCase.jiraDraft,
      sourcesUsed: sources,
      warnings: ['This is a draft for human review.'],
      requirementCase,
      scorecard,
    };
  }

  reviewPr(input: PrReviewInput): PrReviewResult {
    const changedFiles = extractChangedFiles(input.diffText);
    const relatedCode = relatedCodeForChangedFiles(changedFiles);
    const sources = this.searchKnowledge({
      query: `${input.diffText} ${input.jiraContext}`,
      app: input.app,
      component: input.component,
      topK: input.topK,
    });
    const addedLines = countLines(input.diffText, '+');
    const removedLines = countLines(input.diffText, '-');
    const risk = addedLines + removedLines > 80 ? 'High' : addedLines > 25 ? 'Medium' : 'Low';
    const run = this.createRun('pr_review_summary', input.teamId, input.app, 'needs_review', sources, [
      ...changedFiles,
      ...relatedCode.map((file) => file.path),
    ]);
    const scorecard = createScorecard({
      targetType: 'pr_review',
      targetId: run.runId,
      overallScore: relatedCode.length ? 8.4 : 6.4,
      sourcePaths: [...sources.map((source) => source.sourcePath), ...relatedCode.map((file) => file.path)],
      recommendations: [
        'Ask reviewers to confirm idempotency and retry boundaries.',
        'Check that changed source files have matching tests or explicit test-gap notes.',
      ],
    });
    this.scorecardsState.update((cards) => [scorecard, ...cards]);

    const sourceLines = sources.map((source) => `- ${source.title} (${source.sourcePath})`).join('\n');
    const codeLines = relatedCode.map((file) => `- ${file.path}: ${file.summary}`).join('\n');
    const markdown = `# AI PR Review Summary

This is an AI-generated review aid. It does not approve, reject, merge, or block the PR. Human review is required.

## Overall Risk
${risk}

## Changed Files
${changedFiles.map((file) => `- ${file}`).join('\n') || '- No changed files were detected in the synthetic diff.'}

## Related Codebase Memory
${codeLines || '- No codebase memory matched the changed files. Review used document and diff context only.'}

## Business Logic Alignment
The change should be reviewed against DFP Job, Workflow, Task, and Execution semantics. Status and output behavior must remain explicit at task level and execution level.

## Component Impact
- Backend services may affect StatusTracker, OutputCollector, and ExecutionService.
- Frontend monitor behavior should align with polling and stale-state rules.
- Operations runbooks may need an update if retry or stuck-state behavior changes.

## Test Coverage Comments
- Verify status transition tests for QUEUED, RUNNING, FAILED, COMPLETED, CANCELLED, and PARTIAL_SUCCESS.
- Add or confirm duplicate-output and idempotency tests when OutputCollector changes.
- Human review is required before any TestGen output is accepted.

## Runtime / Operational Risk
- Watch for stuck RUNNING states when processors finish but persistence fails.
- Confirm BATCH_TASK timeout handling is visible to Operator workflows.

## Suggested Reviewer Questions
- Does this change preserve task-level status evidence for Analyst and Operator views?
- Are retry/idempotency boundaries visible in tests?
- Should a runbook or historical incident note be updated?

## Sources Used
${sourceLines || '- No matching sources were retrieved.'}
`;

    return {
      run,
      markdown,
      risk,
      sourcesUsed: sources,
      warnings: ['Human review is required before using this summary.'],
      changedFiles,
      relatedCode,
      scorecard,
    };
  }

  planTestGenStub(input: TestGenStubInput): TestGenStubPlan {
    return {
      runId: `testgen-plan-${Date.now().toString(36)}`,
      providerName: 'mock',
      targetSummary: `${input.targetLanguage.toUpperCase()} repo at ${input.repoPath}`,
      plannedActions: [
        'Inspect target metadata using mock data only.',
        'Prepare candidate test targets without modifying the repo.',
        'Keep JTestGen or other engines behind the TestGenProvider contract.',
      ],
      warnings: ['Unit-test generation engine is intentionally excluded from this UI phase.'],
    };
  }

  runTestGenStub(input: TestGenStubInput): TestGenStubResult {
    const run = this.createRun('testgen_stub', input.teamId, 'BatchJobDemo', 'stub_only', []);
    const warnings = [
      'No target repository files were modified.',
      'No unit-test generation engine was executed.',
      'Human review is required for any future generated tests.',
    ];
    const scorecard = createScorecard({
      targetType: 'testgen_report',
      targetId: run.runId,
      overallScore: 8,
      sourcePaths: [],
      recommendations: ['Keep test generation as a provider integration until JTestGen is explicitly configured.'],
    });
    this.scorecardsState.update((cards) => [scorecard, ...cards]);
    return {
      run,
      status: 'stub_only',
      generatedFiles: [],
      warnings,
      scorecard,
      reportMarkdown: `# TestGen Stub Report

Run ID: ${run.runId}
Provider: mock
Dry run: ${input.dryRun}
Repo path: ${input.repoPath}
Target language: ${input.targetLanguage}

No unit tests were generated. This mock report only validates DREAM's plugin workflow surface.

## Candidate Test Targets
- StatusTrackerTest.java
- ExecutionServiceTest.java
- OutputCollectorTest.java

## Warnings
${warnings.map((warning) => `- ${warning}`).join('\n')}
`,
    };
  }

  addRating(rating: Omit<HumanRating, 'createdAt'>): HumanRating {
    const created = {
      ...rating,
      createdAt: new Date().toISOString(),
    };
    this.ratingsState.update((ratings) => [created, ...ratings]);
    return created;
  }

  private createRun(
    useCase: WorkflowType,
    teamId: string,
    app: string,
    status: AuditRun['status'],
    sources: KnowledgeChunk[],
    extraSources: string[] = [],
  ): AuditRun {
    const run: AuditRun = {
      runId: `run_${Date.now().toString(36)}_${Math.floor(Math.random() * 1000)
        .toString()
        .padStart(3, '0')}`,
      useCase,
      teamId,
      app: app || 'ForecastDemo',
      status,
      startedAt: new Date().toISOString(),
      duration: '00:00:04',
      modelProvider: useCase === 'testgen_stub' ? 'mock-testgen' : 'mock-llm',
      modelName: useCase === 'testgen_stub' ? 'mock-testgen-v1' : 'mock-deterministic-v1',
      outputPath: `artifacts/${useCase}-${Date.now().toString(36)}.md`,
      warnings: [],
      sourcesUsed: [...sources.map((source) => source.sourcePath), ...extraSources],
    };
    this.auditRunsState.update((runs) => [run, ...runs]);
    return run;
  }
}

function buildRequirementCase(input: {
  rawRequest: string;
  role: string;
  sources: KnowledgeChunk[];
  codeEvidence: CodebaseFile[];
}): RequirementCase {
  const caseId = `case_${Date.now().toString(36)}`;
  const evidence: ContextEvidence[] = [
    ...input.sources.map((source, index) => ({
      evidenceId: `doc-${index + 1}`,
      title: source.title,
      sourcePath: source.sourcePath,
      sourceType: source.sourceType,
      excerpt: source.excerpt,
      relevanceScore: Math.max(0.68, 0.95 - index * 0.05),
      reason: `Matched concepts: ${source.concepts.slice(0, 3).join(', ')}`,
    })),
    ...input.codeEvidence.map((file, index) => ({
      evidenceId: `code-${index + 1}`,
      title: file.path.split('/').pop() || file.path,
      sourcePath: file.path,
      sourceType: file.role === 'test' ? ('test_file' as const) : ('code_file' as const),
      excerpt: file.summary,
      relevanceScore: Math.max(0.62, 0.9 - index * 0.04),
      reason: `Code concepts: ${file.concepts.slice(0, 3).join(', ')}`,
    })),
  ];

  const impactMap: ImpactItem[] = [
    {
      areaType: 'workflow',
      name: 'Long-running execution workflow',
      description: 'Clarify how Job, Workflow, Task, and Execution statuses progress across async work.',
      confidence: 0.94,
      sources: ['execution-model.md', 'status-tracking-design.md'],
      reason: 'The request asks users to see which task is still running.',
    },
    {
      areaType: 'frontend',
      name: 'Execution Monitor',
      description: 'Show task-level progress, stale polling state, retry affordance, and safe error copy.',
      confidence: 0.88,
      sources: ['execution-monitor.component.ts', 'PR-502'],
      reason: 'DFP historical work added polling and reviewers flagged stale UI states.',
    },
    {
      areaType: 'backend',
      name: 'StatusTracker and ExecutionService',
      description: 'Persist authoritative status transitions and expose task-level status to APIs.',
      confidence: 0.92,
      sources: ['StatusTracker.java', 'ExecutionService.java', 'INC-103'],
      reason: 'Historical incident INC-103 was caused by a failed COMPLETED persistence update.',
    },
    {
      areaType: 'api',
      name: 'ExecutionController status endpoint',
      description: 'Confirm response shape includes execution status, task statuses, timestamps, and terminal state.',
      confidence: 0.84,
      sources: ['ExecutionController.java', 'DFP-101'],
      reason: 'Both UI polling and operator investigation depend on API contract stability.',
    },
    {
      areaType: 'test',
      name: 'Status transition regression tests',
      description: 'Cover stuck RUNNING, failed BATCH_TASK, partial completion, and cancelled execution.',
      confidence: 0.9,
      sources: ['StatusTrackerTest.java', 'status-transition-test-plan.md'],
      reason: 'Status behavior has repeated historical defects and explicit test plans.',
    },
    {
      areaType: 'ops',
      name: 'Stuck running runbook',
      description: 'Update operator steps for processor completed but tracker persistence failed.',
      confidence: 0.78,
      sources: ['status-stuck-running-runbook.md', 'INC-103'],
      reason: 'Operator needs a deterministic response when execution remains RUNNING.',
    },
  ];

  const questions = buildQuestions();
  const sourcesUsed = evidence.map((item) => `- ${item.title} (${item.sourcePath})`).join('\n');
  const impactLines = impactMap
    .map((item) => `- ${item.areaType.toUpperCase()} - ${item.name}: ${item.description}`)
    .join('\n');
  const questionLines = questions
    .map((question) => `- ${question.targetRole}: ${question.question} (${question.whyItMatters})`)
    .join('\n');

  const engineeringBrief = `# Engineering Brief

## 1. Request Summary
${input.rawRequest}

## 2. Interpreted Intent
The user likely needs task-level async status visibility for long-running DFP forecast executions. This is a draft for human review.

## 3. Current Understanding
DREAM retrieved DFP domain, architecture, incident, historical Jira/PR, testing, and codebase memory. Evidence points to Execution Monitor, StatusTracker, ExecutionService, BatchJobAdapter, and status-transition tests.

## 4. Impact Map
${impactLines}

## 5. Relevant Evidence
${sourcesUsed}

## 6. Role-specific Clarification Questions
${questionLines}

## 7. Proposed Implementation Notes
- Prefer an explicit task-level status model shared by SERVICE_TASK and BATCH_TASK.
- Persist status transitions through StatusTracker before updating UI polling state.
- Include stale-state and retry rules in the API response contract.

## 8. Test Strategy
- Add StatusTracker regression tests for stuck RUNNING and terminal-state updates.
- Add Execution Monitor UI tests for stale polling and task-level progress display.
- Confirm BATCH_TASK timeout and PARTIAL_SUCCESS behavior.

## 9. Risks and Unknowns
- UI polling interval and timeout threshold are not yet defined.
- Partial completion behavior may require BA and TL sign-off.
- Operator runbook update may be needed before release.

## 10. Review Checklist
- Source-backed requirement language.
- Codebase memory cites backend, frontend, and tests.
- Historical incidents and PR comments are visible.

## 11. Sources Used
${sourcesUsed}
`;

  const jiraDraft = `# Jira Story Draft

This is a draft for human review.

## Title
Show task-level async status for long-running forecast executions

## User Story
As an Analyst, I want to see which Task is currently running when a Job takes a long time, so that I can understand progress without asking an Operator.

## Business Goal
Reduce uncertainty during long-running DFP forecast executions and make stuck or failed work easier to triage.

## In Scope
- Execution Monitor displays job-level and task-level status.
- Backend status endpoint includes task statuses and terminal state.
- StatusTracker persists QUEUED, RUNNING, FAILED, COMPLETED, CANCELLED, and PARTIAL_SUCCESS transitions.
- Operator runbook references stuck RUNNING detection.

## Out of Scope
- Production TestGen execution.
- Real GitHub or Jira posting.
- Replacing the DFP workflow engine.

## Acceptance Criteria
- Analyst can identify the current running Task for a long-running Execution.
- UI clearly distinguishes PENDING, QUEUED, RUNNING, FAILED, COMPLETED, SKIPPED, and RETRYING task states.
- Stuck RUNNING behavior has a defined timeout and Operator escalation note.
- Status transition tests cover successful, failed, cancelled, and partial completion paths.

## Dev Notes
- Frontend: execution-monitor.component.ts and job-api.service.ts.
- Backend: ExecutionController.java, ExecutionService.java, StatusTracker.java.
- Batch integration: BatchJobAdapter.java.

## Test Scenarios
- SERVICE_TASK completes and UI updates without page refresh.
- BATCH_TASK times out and status becomes FAILED with safe user message.
- Processor finishes but StatusTracker persistence fails; runbook path is visible.
- One Task fails after previous Tasks completed; PARTIAL_SUCCESS behavior is reviewed.

## Open Questions
- What status labels should Analysts see at job level versus task level?
- Should the Execution Monitor poll or use a future subscription mechanism?
- What timeout threshold defines stuck RUNNING?

## Sources Used
${sourcesUsed}
`;

  return {
    caseId,
    title: 'Async status tracking for long-running forecast executions',
    rawRequest: input.rawRequest,
    createdByRole: input.role,
    status: 'brief_generated',
    confidence: 0.86,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    evidence,
    impactMap,
    questions,
    engineeringBrief,
    jiraDraft,
  };
}

function buildQuestions(): RequirementCase['questions'] {
  return [
    {
      targetRole: 'BA',
      question: 'What status labels should users see at job level, task level, or both?',
      whyItMatters: 'Acceptance criteria depend on business-visible status language.',
      relatedSources: ['job-lifecycle.md', 'execution-model.md'],
    },
    {
      targetRole: 'TL',
      question: 'Should SERVICE_TASK and BATCH_TASK share one persisted status model?',
      whyItMatters: 'A split model can create cross-layer drift and review risk.',
      relatedSources: ['service-vs-batch-task.md', 'StatusTracker.java'],
    },
    {
      targetRole: 'FE',
      question: 'Should the Execution Monitor poll, refresh manually, or later subscribe to updates?',
      whyItMatters: 'Frontend behavior affects perceived freshness and API load.',
      relatedSources: ['execution-monitor.component.ts', 'PR-502'],
    },
    {
      targetRole: 'BE',
      question: 'What is the authoritative source for task status after processor completion?',
      whyItMatters: 'INC-103 showed that processor success and persisted status can diverge.',
      relatedSources: ['INC-103', 'StatusTracker.java'],
    },
    {
      targetRole: 'QA',
      question: 'What regression tests prove stuck RUNNING and PARTIAL_SUCCESS behavior?',
      whyItMatters: 'Historical defects cluster around terminal-state and partial-state transitions.',
      relatedSources: ['status-transition-test-plan.md', 'partial-completion-test-plan.md'],
    },
    {
      targetRole: 'OPS',
      question: 'What runbook update is needed when execution remains RUNNING after processor completion?',
      whyItMatters: 'Operators need deterministic triage steps and safe escalation guidance.',
      relatedSources: ['status-stuck-running-runbook.md', 'INC-103'],
    },
  ];
}

function createScorecard(input: {
  targetType: EvaluationScorecard['targetType'];
  targetId: string;
  overallScore: number;
  sourcePaths: string[];
  recommendations: string[];
}): EvaluationScorecard {
  const dimensions: EvaluationDimension[] = [
    buildDimension('completeness', input.overallScore + 0.1, 'Required sections are present and specific.'),
    buildDimension('evidence_quality', input.sourcePaths.length ? 8.8 : 5.2, 'Output cites retrievable DFP memory sources.'),
    buildDimension('impact_accuracy', input.overallScore, 'Impact map covers UI, backend, workflow, tests, and ops.'),
    buildDimension('test_awareness', 8.2, 'Status transition and output idempotency tests are called out.'),
    buildDimension('historical_context', 8.4, 'Historical Jira, PR, and incident references are visible.'),
    buildDimension('hallucination_risk', 8.7, 'Claims stay within synthetic DemoCorp evidence.'),
  ];
  return {
    evaluationId: `eval_${Date.now().toString(36)}_${Math.floor(Math.random() * 100)}`,
    targetType: input.targetType,
    targetId: input.targetId,
    overallScore: input.overallScore,
    grade: gradeForScore(input.overallScore),
    passStatus: input.overallScore >= 7 ? 'pass' : input.overallScore >= 5.5 ? 'warning' : 'fail',
    sourceCoverage: buildSourceCoverage(input.sourcePaths),
    dimensions,
    missingCriticalItems: input.overallScore >= 7 ? [] : ['Insufficient codebase memory coverage.'],
    recommendations: input.recommendations,
  };
}

function buildDimension(name: string, score: number, rationale: string): EvaluationDimension {
  return {
    name,
    score: Math.min(10, Math.max(0, Number(score.toFixed(1)))),
    weight: 1,
    passed: score >= 7,
    rationale,
    evidence: ['DFP mock data', 'source-backed markdown output'],
    missingItems: score >= 7 ? [] : ['More source coverage required.'],
    recommendations: score >= 7 ? [] : ['Retrieve additional knowledge and codebase memory before review.'],
  };
}

function buildSourceCoverage(paths: string[]): Record<string, boolean> {
  const joined = paths.join(' ').toLowerCase();
  return {
    domainDocs: joined.includes('/domain/'),
    architectureDocs: joined.includes('/architecture/'),
    runbooks: joined.includes('/runbooks/'),
    incidents: joined.includes('/incidents/') || joined.includes('inc-'),
    historicalJira: joined.includes('/historical-jira/') || joined.includes('dfp-'),
    historicalPr: joined.includes('/historical-pr/') || joined.includes('pr-'),
    testingDocs: joined.includes('/testing/') || joined.includes('test'),
    conceptMemory: joined.includes('/concepts/'),
    codeFiles: joined.includes('.java') || joined.includes('.ts') || joined.includes('.py'),
    testFiles: joined.toLowerCase().includes('test'),
  };
}

function gradeForScore(score: number): EvaluationScorecard['grade'] {
  if (score >= 8.5) {
    return 'A';
  }
  if (score >= 7) {
    return 'B';
  }
  if (score >= 5.5) {
    return 'C';
  }
  if (score >= 4) {
    return 'D';
  }
  return 'F';
}

function tokenize(value: string): string[] {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

function searchTextForChunk(chunk: KnowledgeChunk): string {
  return `${chunk.title} ${chunk.excerpt} ${chunk.sourcePath} ${chunk.concepts.join(' ')} ${chunk.metadata.component}`;
}

function searchTextForFile(file: CodebaseFile): string {
  return `${file.path} ${file.summary} ${file.concepts.join(' ')} ${file.symbols.join(' ')} ${file.relatedTests.join(' ')}`;
}

function scoreSearchText(text: string, terms: string[]): number {
  const haystack = text.toLowerCase();
  return terms.reduce((score, term) => {
    const occurrences = haystack.split(term).length - 1;
    return score + occurrences * (term.length > 4 ? 2 : 1);
  }, 0);
}

function countLines(diffText: string, prefix: '+' | '-'): number {
  return diffText
    .split('\n')
    .filter((line) => line.startsWith(prefix) && !line.startsWith(`${prefix}${prefix}${prefix}`)).length;
}

function extractChangedFiles(diffText: string): string[] {
  return Array.from(
    new Set(
      diffText
        .split('\n')
        .filter((line) => line.startsWith('diff --git '))
        .map((line) => line.match(/ b\/(.+)$/)?.[1])
        .filter((value): value is string => Boolean(value)),
    ),
  );
}

function relatedCodeForChangedFiles(changedFiles: string[]): CodebaseFile[] {
  const fileNames = changedFiles.map((file) => file.split('/').pop()?.toLowerCase() || file.toLowerCase());
  const direct = MOCK_CODEBASE_FILES.filter((file) => fileNames.includes(file.path.split('/').pop()?.toLowerCase() || ''));
  const conceptTerms = changedFiles.join(' ').toLowerCase();
  const conceptMatches = MOCK_CODEBASE_FILES.filter((file) =>
    file.concepts.some((concept) => conceptTerms.includes(concept.replace(/\s+/g, '-')) || conceptTerms.includes(concept)),
  );
  return Array.from(new Map([...direct, ...conceptMatches].map((file) => [file.id, file])).values()).slice(0, 6);
}

function cloneKnowledgeIntakeItem(item: KnowledgeIntakeItem): KnowledgeIntakeItem {
  return {
    ...item,
    parsedConcepts: [...item.parsedConcepts],
    sections: item.sections.map((section) => ({
      ...section,
      concepts: [...section.concepts],
    })),
    reviewNotes: [...item.reviewNotes],
  };
}

function cloneContextIntelligenceSnapshot(snapshot: ContextIntelligenceSnapshot): ContextIntelligenceSnapshot {
  return {
    ...snapshot,
    retrievalTrail: snapshot.retrievalTrail.map((step) => ({ ...step })),
    contextPackSections: snapshot.contextPackSections.map((section) => ({
      ...section,
      includedEvidenceIds: [...section.includedEvidenceIds],
    })),
    promptPreview: {
      ...snapshot.promptPreview,
      evidenceInstructions: [...snapshot.promptPreview.evidenceInstructions],
    },
    metrics: snapshot.metrics.map((metric) => ({ ...metric })),
    evidenceCards: snapshot.evidenceCards.map((card) => ({ ...card })),
    logicChain: snapshot.logicChain.map((step) => ({
      ...step,
      evidenceIds: [...step.evidenceIds],
    })),
  };
}

const MOCK_PACKS: KnowledgePack[] = [
  {
    id: 'dfp-domain',
    name: 'DFP Domain Memory',
    app: 'ForecastDemo',
    component: 'job-workflow-task-execution',
    docType: 'domain',
    status: 'Healthy',
    coverage: 96,
    updatedAt: '2026-06-20',
  },
  {
    id: 'dfp-architecture',
    name: 'Architecture and Codebase Memory',
    app: 'ForecastDemo',
    component: 'platform',
    docType: 'architecture',
    status: 'Healthy',
    coverage: 91,
    updatedAt: '2026-06-20',
  },
  {
    id: 'dfp-history',
    name: 'Historical Jira, PR, and Incident Memory',
    app: 'ForecastDemo',
    component: 'delivery-history',
    docType: 'historical',
    status: 'Healthy',
    coverage: 88,
    updatedAt: '2026-06-20',
  },
  {
    id: 'dfp-runbooks',
    name: 'Operator Runbooks',
    app: 'BatchJobDemo',
    component: 'operations',
    docType: 'runbooks',
    status: 'Warning',
    coverage: 74,
    updatedAt: '2026-06-19',
  },
  {
    id: 'dfp-evals',
    name: 'Evaluation Profiles',
    app: 'ForecastDemo',
    component: 'quality-gates',
    docType: 'eval_profiles',
    status: 'Healthy',
    coverage: 84,
    updatedAt: '2026-06-20',
  },
];

const MOCK_CHUNKS: KnowledgeChunk[] = [
  {
    id: 'chunk-job-lifecycle',
    title: 'Job Lifecycle and Execution Workflow',
    sourcePath: 'knowledge_packs/demo_team/docs/domain/job-lifecycle.md',
    excerpt:
      'A DFP Job is created by an Analyst, bound to a Workflow, executed asynchronously, and monitored through task-level Execution status including failure handling.',
    concepts: ['job execution', 'workflow', 'task status', 'failure'],
    sourceType: 'domain_doc',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'job-execution',
      docType: 'domain',
    },
  },
  {
    id: 'chunk-status-design',
    title: 'Status Tracking Design',
    sourcePath: 'knowledge_packs/demo_team/docs/architecture/status-tracking-design.md',
    excerpt:
      'Execution status is persisted by StatusTracker and displayed by Execution Monitor. Terminal states must not depend on transient processor memory.',
    concepts: ['execution status', 'task status', 'async tracking', 'polling', 'status stuck running'],
    sourceType: 'architecture_doc',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'job-execution',
      docType: 'architecture',
    },
  },
  {
    id: 'chunk-stuck-running',
    title: 'INC-103 Status Stuck RUNNING',
    sourcePath: 'knowledge_packs/demo_team/docs/incidents/INC-103-status-stuck-running.md',
    excerpt:
      'Python processor completed successfully, but StatusTracker failed to persist COMPLETED. UI continued showing RUNNING and Operator investigation was delayed.',
    concepts: ['status stuck running', 'status tracker', 'operator runbook', 'processor completion'],
    sourceType: 'incident',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'job-execution',
      docType: 'incidents',
    },
  },
  {
    id: 'chunk-batch-job-failure',
    title: 'Batch Job Failure Runbook',
    sourcePath: 'knowledge_packs/demo_team/docs/runbooks/batch-job-failure-runbook.md',
    excerpt:
      'BatchJobDemo operators confirm job execution id, task status, failed batch reason, retry eligibility, and safe user-facing failure details.',
    concepts: ['job execution failure', 'batch task', 'operator runbook', 'retry'],
    sourceType: 'runbook',
    metadata: {
      teamId: 'demo_team',
      app: 'BatchJobDemo',
      component: 'job-execution',
      docType: 'runbooks',
    },
  },
  {
    id: 'chunk-output-idempotency',
    title: 'INC-102 Duplicate Output',
    sourcePath: 'knowledge_packs/demo_team/docs/incidents/INC-102-duplicate-output.md',
    excerpt:
      'OutputCollector retried after a transient storage error without an idempotency key, producing duplicate result files for one Execution.',
    concepts: ['duplicate output', 'output collection', 'idempotency', 'storage retry'],
    sourceType: 'incident',
    metadata: {
      teamId: 'demo_team',
      app: 'OutputPreviewDemo',
      component: 'output-collection',
      docType: 'incidents',
    },
  },
  {
    id: 'chunk-partial-completion',
    title: 'INC-105 Partial Completion Undefined',
    sourcePath: 'knowledge_packs/demo_team/docs/incidents/INC-105-partial-completion-undefined.md',
    excerpt:
      'One Task failed while other Tasks completed. Product behavior for PARTIAL_SUCCESS and partial result availability was not defined.',
    concepts: ['partial completion', 'partial success', 'task failure', 'output availability'],
    sourceType: 'incident',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'job-execution',
      docType: 'incidents',
    },
  },
  {
    id: 'chunk-dfp-101',
    title: 'DFP-101 Add Execution Status Tracking',
    sourcePath: 'knowledge_packs/demo_team/docs/historical-jira/DFP-101-add-execution-status-tracking.md',
    excerpt:
      'Historical story introduced async execution status, task status visibility, and acceptance criteria for Analyst progress monitoring.',
    concepts: ['execution status', 'jira history', 'acceptance criteria', 'analyst'],
    sourceType: 'historical_jira',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'job-execution',
      docType: 'historical-jira',
    },
  },
  {
    id: 'chunk-pr-502',
    title: 'PR-502 Add Execution Status Polling',
    sourcePath: 'knowledge_packs/demo_team/docs/historical-pr/PR-502-add-execution-status-polling.md',
    excerpt:
      'Reviewer noted backend status updates were present but Execution Monitor error and stale polling states needed follow-up.',
    concepts: ['execution monitor', 'polling', 'frontend status', 'review comment'],
    sourceType: 'historical_pr',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'job-execution',
      docType: 'historical-pr',
    },
  },
  {
    id: 'chunk-output-preview',
    title: 'Output Preview Design',
    sourcePath: 'knowledge_packs/demo_team/docs/architecture/output-preview-design.md',
    excerpt:
      'Large result files use paginated preview and Athena-style query paths. Full file loads are blocked after preview OOM incident INC-104.',
    concepts: ['output preview', 'large file preview', 'pagination', 'athena preview'],
    sourceType: 'architecture_doc',
    metadata: {
      teamId: 'demo_team',
      app: 'OutputPreviewDemo',
      component: 'output-preview',
      docType: 'architecture',
    },
  },
  {
    id: 'chunk-test-plan',
    title: 'Status Transition Test Plan',
    sourcePath: 'knowledge_packs/demo_team/docs/testing/status-transition-test-plan.md',
    excerpt:
      'Regression tests cover QUEUED, RUNNING, FAILED, COMPLETED, CANCELLED, PARTIAL_SUCCESS, and stuck RUNNING recovery paths.',
    concepts: ['status transition tests', 'regression', 'partial success', 'stuck running'],
    sourceType: 'testing_doc',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'testing',
      docType: 'testing',
    },
  },
  {
    id: 'chunk-concept-execution',
    title: 'Concept Memory: Execution Status',
    sourcePath: 'knowledge_packs/demo_team/docs/concepts/execution-status-memory.md',
    excerpt:
      'Execution status links Analyst UI, Java StatusTracker, AWS orchestration, Python processors, incidents, PR history, and test plans.',
    concepts: ['concept memory', 'execution status', 'codebase memory', 'role questions'],
    sourceType: 'concept_memory',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'job-execution',
      docType: 'concepts',
    },
  },
  {
    id: 'chunk-review-checklist',
    title: 'Async Execution Review Checklist',
    sourcePath: 'knowledge_packs/demo_team/docs/pr-review/async-execution-review-checklist.md',
    excerpt:
      'Check requirement alignment, missing tests, status transition completeness, operational risk, UI polling, and runbook impact.',
    concepts: ['pr review', 'async execution', 'missing tests', 'operational risk'],
    sourceType: 'concept_memory',
    metadata: {
      teamId: 'demo_team',
      app: 'ForecastDemo',
      component: 'job-execution',
      docType: 'pr-review',
    },
  },
];

const MOCK_KNOWLEDGE_INTAKE_QUEUE: KnowledgeIntakeItem[] = [
  {
    id: 'intake-runbook-stuck-running',
    title: 'Status Stuck RUNNING Operator Runbook',
    sourceKind: 'runbook',
    sourcePath: 'uploads/runbooks/status-stuck-running-runbook.md',
    owner: 'Ops Enablement',
    importedAt: '2026-06-21T14:12:00.000Z',
    queueStatus: 'ready_for_review',
    reviewStatus: 'needs_review',
    targetPack: 'DFP Operations Memory',
    parser: 'markdown-runbook-parser-v1',
    parsedConcepts: ['stuck running', 'operator escalation', 'status tracker', 'processor completion'],
    sections: [
      {
        id: 'runbook-section-detect',
        heading: 'Detect stuck RUNNING execution',
        summary: 'Operator compares processor completion evidence with StatusTracker terminal-state persistence.',
        concepts: ['stuck running', 'status tracker', 'terminal state'],
        confidence: 0.92,
      },
      {
        id: 'runbook-section-remediate',
        heading: 'Safe remediation path',
        summary: 'Escalate before manual status correction and attach execution id, processor log id, and failed persistence event.',
        concepts: ['operator escalation', 'audit trail', 'manual correction'],
        confidence: 0.87,
      },
      {
        id: 'runbook-section-prevent',
        heading: 'Regression prevention',
        summary: 'Require StatusTracker tests for RUNNING to COMPLETED and RUNNING to FAILED persistence failures.',
        concepts: ['regression tests', 'status transition tests', 'persistence failure'],
        confidence: 0.9,
      },
    ],
    reviewNotes: [
      'Ops reviewer must confirm manual correction language before promotion.',
      'Promote into operations pack only after incident owner approves terminology.',
    ],
    promotionSummary: 'Adds operator-ready stuck RUNNING remediation context to requirement and PR review retrieval.',
  },
  {
    id: 'intake-docx-long-running',
    title: 'Long-running Forecast Execution UX Notes',
    sourceKind: 'docx',
    sourcePath: 'uploads/docx/long-running-forecast-execution-ux-notes.docx',
    owner: 'Product BA',
    importedAt: '2026-06-21T15:05:00.000Z',
    queueStatus: 'parsed',
    reviewStatus: 'unreviewed',
    targetPack: 'DFP Domain Memory',
    parser: 'docx-section-parser-v1',
    parsedConcepts: ['analyst progress', 'task status labels', 'partial success', 'safe error copy'],
    sections: [
      {
        id: 'docx-section-analyst-progress',
        heading: 'Analyst progress expectation',
        summary: 'Analysts need job-level and task-level progress without asking Operators during long forecasts.',
        concepts: ['analyst progress', 'task status', 'job execution'],
        confidence: 0.89,
      },
      {
        id: 'docx-section-status-labels',
        heading: 'Visible task status labels',
        summary: 'The UI should distinguish queued, running, failed, completed, cancelled, skipped, and retrying tasks.',
        concepts: ['status labels', 'queued', 'retrying', 'cancelled'],
        confidence: 0.84,
      },
      {
        id: 'docx-section-partial-success',
        heading: 'Partial completion question',
        summary: 'Product still needs a decision on when partial output is available after optional task failure.',
        concepts: ['partial success', 'open question', 'output availability'],
        confidence: 0.78,
      },
    ],
    reviewNotes: [
      'Needs BA/TL review because partial success is still an open product decision.',
      'Parsed headings look stable; concept merge is pending.',
    ],
    promotionSummary: 'Would enrich requirement drafting with product wording for progress visibility and open questions.',
  },
  {
    id: 'intake-confluence-state-model',
    title: 'Confluence HLD: Forecast Execution State Model',
    sourceKind: 'confluence_hld',
    sourcePath: 'confluence://DFP/HLD/Forecast-Execution-State-Model',
    owner: 'Platform TL',
    importedAt: '2026-06-21T16:40:00.000Z',
    queueStatus: 'promoted',
    reviewStatus: 'promoted',
    targetPack: 'DFP Architecture Memory',
    parser: 'confluence-hld-parser-v1',
    parsedConcepts: ['state machine', 'terminal states', 'batch task retry', 'api contract'],
    sections: [
      {
        id: 'hld-section-state-machine',
        heading: 'Execution state machine',
        summary: 'Defines legal transitions for queued, running, completed, failed, cancelled, and partial success.',
        concepts: ['state machine', 'terminal states', 'legal transitions'],
        confidence: 0.95,
      },
      {
        id: 'hld-section-api-contract',
        heading: 'Status API contract',
        summary: 'Status endpoint returns execution state, task states, timestamps, stale flag, and retry hint.',
        concepts: ['api contract', 'stale flag', 'retry hint'],
        confidence: 0.91,
      },
      {
        id: 'hld-section-retry',
        heading: 'Batch retry behavior',
        summary: 'Batch task retries preserve execution id and make failure reason visible to Operator workflows.',
        concepts: ['batch task retry', 'failure reason', 'operator workflow'],
        confidence: 0.88,
      },
    ],
    reviewNotes: [
      'Already promoted in mock state to show post-approval queue behavior.',
      'Architecture owner accepted status API contract wording.',
    ],
    promotionSummary: 'Promoted sections now participate in graph expansion and context pack assembly.',
  },
];

const MOCK_CODEBASE_FILES: CodebaseFile[] = [
  {
    id: 'code-execution-monitor',
    path: 'examples/dfp-demo-repo/frontend/src/app/execution/execution-monitor.component.ts',
    layer: 'frontend',
    language: 'typescript',
    role: 'source',
    summary: 'Angular component that renders job and task status, polling state, stale data warnings, and operator-facing retry hints.',
    concepts: ['execution status', 'task status', 'polling', 'stuck running'],
    symbols: ['ExecutionMonitorComponent', 'refreshStatus', 'renderTaskProgress'],
    relatedTests: [],
  },
  {
    id: 'code-job-api',
    path: 'examples/dfp-demo-repo/frontend/src/app/services/job-api.service.ts',
    layer: 'frontend',
    language: 'typescript',
    role: 'source',
    summary: 'Angular service wrapper for Job, Execution, and Output Preview API calls used by DFP frontend pages.',
    concepts: ['api contract', 'execution status', 'output preview'],
    symbols: ['JobApiService', 'getExecutionStatus', 'previewOutput'],
    relatedTests: [],
  },
  {
    id: 'code-execution-controller',
    path: 'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/execution/ExecutionController.java',
    layer: 'backend',
    language: 'java',
    role: 'source',
    summary: 'Spring-style REST controller exposing job execution start, status lookup, cancellation, and task-level execution state.',
    concepts: ['execution status', 'api', 'job execution', 'task status'],
    symbols: ['ExecutionController', 'startExecution', 'getExecutionStatus'],
    relatedTests: ['ExecutionServiceTest.java'],
  },
  {
    id: 'code-execution-service',
    path: 'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/execution/ExecutionService.java',
    layer: 'backend',
    language: 'java',
    role: 'source',
    summary: 'Coordinates workflow tasks, status transitions, service task handling, batch adapter calls, and output collection.',
    concepts: ['execution service', 'workflow', 'batch task', 'partial success'],
    symbols: ['ExecutionService', 'start', 'markTaskComplete', 'markTaskFailed'],
    relatedTests: ['ExecutionServiceTest.java'],
  },
  {
    id: 'code-status-tracker',
    path: 'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java',
    layer: 'backend',
    language: 'java',
    role: 'source',
    summary: 'Persists authoritative ExecutionStatus and TaskStatus transitions to prevent stale RUNNING state after processor completion.',
    concepts: ['status tracker', 'execution status', 'task status', 'stuck running'],
    symbols: ['StatusTracker', 'transitionExecution', 'transitionTask', 'isTerminal'],
    relatedTests: ['StatusTrackerTest.java'],
  },
  {
    id: 'code-batch-adapter',
    path: 'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/adapters/BatchJobAdapter.java',
    layer: 'backend',
    language: 'java',
    role: 'source',
    summary: 'Adapter for heavy BATCH_TASK orchestration with timeout, retry, and failure-status mapping hints.',
    concepts: ['batch task', 'timeout', 'retry', 'operator runbook'],
    symbols: ['BatchJobAdapter', 'submitBatchTask', 'readBatchStatus'],
    relatedTests: ['ExecutionServiceTest.java'],
  },
  {
    id: 'code-output-collector',
    path: 'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java',
    layer: 'backend',
    language: 'java',
    role: 'source',
    summary: 'Collects output artifacts from storage and uses idempotency keys to prevent duplicate result files after retry.',
    concepts: ['output collection', 'idempotency', 'duplicate output', 'storage retry'],
    symbols: ['OutputCollector', 'collect', 'buildIdempotencyKey'],
    relatedTests: ['OutputCollectorTest.java'],
  },
  {
    id: 'code-output-preview',
    path: 'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/output/OutputPreviewService.java',
    layer: 'backend',
    language: 'java',
    role: 'source',
    summary: 'Chooses paginated object preview or Athena-style query preview for large forecast output artifacts.',
    concepts: ['output preview', 'athena preview', 'large file preview', 'pagination'],
    symbols: ['OutputPreviewService', 'previewArtifact', 'choosePreviewMode'],
    relatedTests: ['OutputPreviewServiceTest.java'],
  },
  {
    id: 'code-input-validator',
    path: 'examples/dfp-demo-repo/python-processors/processors/input_validator.py',
    layer: 'python',
    language: 'python',
    role: 'source',
    summary: 'Python processor validates task-level forecast config before execution and raises structured validation errors.',
    concepts: ['task config validation', 'input validation', 'processor'],
    symbols: ['InputValidator', 'validate_required_fields'],
    relatedTests: ['test_input_validator.py'],
  },
  {
    id: 'code-state-machine',
    path: 'examples/dfp-demo-repo/aws/step-functions/job-execution-state-machine.asl.json',
    layer: 'aws',
    language: 'json',
    role: 'config',
    summary: 'Synthetic Step Functions-like orchestration for SERVICE_TASK and BATCH_TASK routing, retries, and output aggregation.',
    concepts: ['aws orchestration', 'workflow', 'service task', 'batch task'],
    symbols: ['ValidateInput', 'RunServiceTask', 'RunBatchTask', 'CollectOutput'],
    relatedTests: [],
  },
  {
    id: 'test-status-tracker',
    path: 'examples/dfp-demo-repo/backend-api/src/test/java/com/democorp/dfp/execution/StatusTrackerTest.java',
    layer: 'test',
    language: 'java',
    role: 'test',
    summary: 'JUnit-style tests for legal status transitions, terminal-state behavior, and stuck RUNNING regression coverage.',
    concepts: ['status transition tests', 'stuck running', 'terminal state'],
    symbols: ['StatusTrackerTest', 'marksCompleted', 'rejectsInvalidTransition'],
    relatedTests: [],
  },
  {
    id: 'test-output-collector',
    path: 'examples/dfp-demo-repo/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java',
    layer: 'test',
    language: 'java',
    role: 'test',
    summary: 'Tests output collection idempotency and duplicate output prevention after storage retry.',
    concepts: ['output collection tests', 'idempotency', 'duplicate output'],
    symbols: ['OutputCollectorTest', 'doesNotDuplicateArtifacts'],
    relatedTests: [],
  },
];

const MOCK_GRAPH_NODES: EvidenceGraphNode[] = [
  {
    id: 'graph-concept-execution-status',
    type: 'concept',
    title: 'execution status',
    sourcePath: 'evidence-graph#concept:execution-status',
    concepts: ['execution status', 'task status', 'async tracking'],
    summary: 'Connects DFP status docs, UI monitor, backend tracker, incidents, Jira, PRs, and tests.',
  },
  {
    id: 'graph-status-design',
    type: 'architecture_doc',
    title: 'Status Tracking Design',
    sourcePath: 'knowledge_packs/demo_team/docs/architecture/status-tracking-design.md',
    concepts: ['execution status', 'polling'],
    summary: 'Defines persisted status, terminal states, and stale RUNNING handling.',
  },
  {
    id: 'graph-status-tracker',
    type: 'code_file',
    title: 'StatusTracker.java',
    sourcePath: 'backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java',
    concepts: ['execution status', 'status transition'],
    summary: 'Persists authoritative Execution and Task status transitions.',
  },
  {
    id: 'graph-inc-103',
    type: 'incident',
    title: 'INC-103 Status stuck RUNNING',
    sourcePath: 'knowledge_packs/demo_team/docs/incidents/INC-103-status-stuck-running.md',
    concepts: ['status stuck running', 'operator'],
    summary: 'Processor completed but StatusTracker failed to persist COMPLETED.',
  },
  {
    id: 'graph-dfp-101',
    type: 'historical_jira',
    title: 'DFP-101 Add execution status tracking',
    sourcePath: 'knowledge_packs/demo_team/docs/historical-jira/DFP-101-add-execution-status-tracking.md',
    concepts: ['execution status', 'acceptance criteria'],
    summary: 'Historical story for async job and task-level progress visibility.',
  },
  {
    id: 'graph-output-collection',
    type: 'concept',
    title: 'output collection',
    sourcePath: 'evidence-graph#concept:output-collection',
    concepts: ['output collection', 'idempotency'],
    summary: 'Connects OutputCollector, duplicate-output incident, idempotency Jira/PR, and tests.',
  },
  {
    id: 'graph-output-collector',
    type: 'code_file',
    title: 'OutputCollector.java',
    sourcePath: 'backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java',
    concepts: ['output collection', 'idempotency'],
    summary: 'Collects result artifacts and must use a stable idempotency key during retry.',
  },
  {
    id: 'graph-inc-102',
    type: 'incident',
    title: 'INC-102 Duplicate output',
    sourcePath: 'knowledge_packs/demo_team/docs/incidents/INC-102-duplicate-output.md',
    concepts: ['duplicate output', 'storage retry'],
    summary: 'Retry without stable idempotency key produced duplicate result files.',
  },
  {
    id: 'graph-dfp-110',
    type: 'historical_jira',
    title: 'DFP-110 Make output collection idempotent',
    sourcePath: 'knowledge_packs/demo_team/docs/historical-jira/DFP-110-output-collection-idempotency.md',
    concepts: ['output collection', 'idempotency'],
    summary: 'Historical story defining stable output collection idempotency behavior.',
  },
];

const MOCK_GRAPH_PATHS: EvidenceGraphPath[] = [
  {
    id: 'path-execution-status-main',
    concept: 'execution status',
    path: [
      'execution status',
      'Status Tracking Design',
      'StatusTracker.java',
      'StatusTrackerTest.java',
      'INC-103 Status stuck RUNNING',
      'DFP-101 Add execution status tracking',
      'PR-502 Add execution status polling',
    ],
    evidenceTypes: [
      'concept',
      'architecture_doc',
      'code_file',
      'test_file',
      'incident',
      'historical_jira',
      'historical_pr',
    ],
    risk: 'Stale RUNNING state or missing task-level transition could mislead Analyst and Operator views.',
    reviewHint: 'Ask BA/TL whether status is job-level, task-level, or both, then require regression tests.',
  },
  {
    id: 'path-output-idempotency',
    concept: 'output collection',
    path: [
      'output collection',
      'OutputCollector.java',
      'OutputCollectorTest.java',
      'INC-102 Duplicate output',
      'DFP-110 Make output collection idempotent',
      'PR-508 Output collection idempotency',
    ],
    evidenceTypes: ['concept', 'code_file', 'test_file', 'incident', 'historical_jira', 'historical_pr'],
    risk: 'Retry without a stable idempotency key can create duplicate result artifacts.',
    reviewHint: 'Require tests proving retry reuses the same idempotency key and does not duplicate output.',
  },
  {
    id: 'path-output-preview',
    concept: 'output preview',
    path: [
      'output preview',
      'Output Preview Design',
      'OutputPreviewService.java',
      'AthenaPreviewAdapter.java',
      'INC-104 Preview OOM',
      'INC-107 Athena preview timeout',
      'DFP-104 Athena large file preview',
    ],
    evidenceTypes: ['concept', 'architecture_doc', 'code_file', 'incident', 'incident', 'historical_jira'],
    risk: 'Full-file preview or missing partition predicate can create memory and timeout failures.',
    reviewHint: 'Review pagination, partition predicate, timeout messaging, and large-file regression tests.',
  },
  {
    id: 'path-partial-recovery',
    concept: 'partial recovery',
    path: [
      'partial recovery',
      'ExecutionService.java',
      'ExecutionStatus.PARTIAL_SUCCESS',
      'INC-105 Partial completion undefined',
      'DFP-106 Define partial execution recovery',
      'PR-509 Partial success status',
    ],
    evidenceTypes: ['concept', 'code_file', 'code_file', 'incident', 'historical_jira', 'historical_pr'],
    risk: 'Product behavior can be ambiguous when optional tasks fail but outputs still exist.',
    reviewHint: 'Force open questions for BA/TL/QA around partial result availability and retry policy.',
  },
];

const MOCK_CONTEXT_INTELLIGENCE: ContextIntelligenceSnapshot = {
  caseId: 'case_async_status',
  title: 'Async Status Context Pack',
  request:
    'Users want to know which task is still running when a forecast job takes too long. The execution page should show better progress.',
  retrievalTrail: [
    {
      id: 'trail-normalize',
      step: 1,
      label: 'Normalize request',
      detail: 'Mapped rough BA wording to execution status, task status, stale polling, and operator escalation concepts.',
      query: 'long running forecast task still running progress',
      sourcesMatched: 0,
      status: 'pass',
    },
    {
      id: 'trail-knowledge',
      step: 2,
      label: 'Retrieve knowledge chunks',
      detail: 'Pulled domain, architecture, runbook, incident, Jira, PR, testing, and concept memory.',
      query: 'execution status stuck running task status polling partial success',
      sourcesMatched: 8,
      status: 'pass',
    },
    {
      id: 'trail-graph',
      step: 3,
      label: 'Expand evidence graph',
      detail: 'Expanded execution status into code, tests, incidents, historical Jira, and PR review edges.',
      query: 'concept:execution-status hops:2 include:code,test,incident',
      sourcesMatched: 7,
      status: 'pass',
    },
    {
      id: 'trail-codebase',
      step: 4,
      label: 'Bind codebase memory',
      detail: 'Attached ExecutionMonitor, StatusTracker, ExecutionService, BatchJobAdapter, and regression tests.',
      query: 'ExecutionMonitor StatusTracker ExecutionService status transition tests',
      sourcesMatched: 6,
      status: 'pass',
    },
    {
      id: 'trail-eval',
      step: 5,
      label: 'Evaluate context pack',
      detail: 'Checked coverage, contradictions, source freshness, token budget, and human-review guardrails.',
      query: 'eval async-status-tracking source coverage contradictions',
      sourcesMatched: 4,
      status: 'watch',
    },
  ],
  contextPackSections: [
    {
      id: 'pack-request',
      title: 'Request Interpretation',
      summary: 'Keep the user story focused on Analyst progress visibility for long-running forecast executions.',
      includedEvidenceIds: ['evidence-dfp-101', 'evidence-status-design'],
      tokenEstimate: 540,
      guardrail: 'Do not invent final timeout values; ask BA/TL.',
      status: 'pass',
    },
    {
      id: 'pack-evidence',
      title: 'Source-backed Evidence Bundle',
      summary: 'Use architecture, incident, historical Jira, historical PR, testing, and codebase memory together.',
      includedEvidenceIds: ['evidence-status-design', 'evidence-inc-103', 'evidence-pr-502', 'evidence-status-tracker'],
      tokenEstimate: 1780,
      guardrail: 'Every recommendation must cite at least one source path.',
      status: 'pass',
    },
    {
      id: 'pack-impact',
      title: 'Impact and Risk Lens',
      summary: 'Explain frontend, backend, API, tests, and Ops runbook impact without treating draft output as approved.',
      includedEvidenceIds: ['evidence-execution-monitor', 'evidence-status-tracker', 'evidence-test-plan'],
      tokenEstimate: 1120,
      guardrail: 'Keep PR and Jira outputs draft-only until human review.',
      status: 'pass',
    },
    {
      id: 'pack-open-questions',
      title: 'Open Questions',
      summary: 'Surface partial success and stale RUNNING timeout decisions as explicit role-specific questions.',
      includedEvidenceIds: ['evidence-inc-105', 'evidence-test-plan'],
      tokenEstimate: 460,
      guardrail: 'Mark product ambiguity as needs_review instead of filling gaps.',
      status: 'watch',
    },
  ],
  promptPreview: {
    system:
      'You are DREAM, a source-backed engineering copilot. Produce draft-only outputs and require human review.',
    developer:
      'Use only supplied context pack evidence. Preserve source paths, expose uncertainty, and separate facts from recommendations.',
    user:
      'Draft a requirement case for task-level async status visibility in long-running DFP forecast executions.',
    evidenceInstructions: [
      'Cite status-tracking-design.md when describing terminal states.',
      'Cite INC-103 for stuck RUNNING risk and operator escalation.',
      'Cite PR-502 when discussing stale polling and frontend follow-up.',
      'Ask BA/TL/QA questions for partial success and timeout thresholds.',
    ],
  },
  metrics: [
    {
      label: 'Source coverage',
      value: '7 / 8',
      target: '>= 6 source families',
      status: 'pass',
      note: 'Docs, incidents, Jira, PR, tests, code, and concept memory are represented.',
    },
    {
      label: 'Retrieval precision',
      value: '0.86',
      target: '>= 0.80',
      status: 'pass',
      note: 'Top evidence centers on execution status rather than unrelated output preview material.',
    },
    {
      label: 'Conflict flags',
      value: '1',
      target: '0 unresolved',
      status: 'watch',
      note: 'Partial success output availability remains a product decision.',
    },
    {
      label: 'Prompt budget',
      value: '3.9k',
      target: '<= 6k tokens',
      status: 'pass',
      note: 'Context pack leaves room for draft brief, questions, and Jira story generation.',
    },
  ],
  evidenceCards: [
    {
      evidenceId: 'evidence-dfp-101',
      title: 'DFP-101 Add Execution Status Tracking',
      sourcePath: 'knowledge_packs/demo_team/docs/historical-jira/DFP-101-add-execution-status-tracking.md',
      sourceType: 'historical_jira',
      excerpt: 'Historical story introduced async execution status, task status visibility, and Analyst progress monitoring.',
      relevanceScore: 0.91,
      reason: 'Connects the current ask to accepted historical requirement language.',
    },
    {
      evidenceId: 'evidence-status-design',
      title: 'Status Tracking Design',
      sourcePath: 'knowledge_packs/demo_team/docs/architecture/status-tracking-design.md',
      sourceType: 'architecture_doc',
      excerpt: 'Defines persisted execution status, terminal states, task states, and stale RUNNING handling.',
      relevanceScore: 0.96,
      reason: 'Primary architecture source for status model and terminal-state rules.',
    },
    {
      evidenceId: 'evidence-inc-103',
      title: 'INC-103 Status Stuck RUNNING',
      sourcePath: 'knowledge_packs/demo_team/docs/incidents/INC-103-status-stuck-running.md',
      sourceType: 'incident',
      excerpt: 'Processor completed but StatusTracker failed to persist COMPLETED, leaving the user-facing execution stuck.',
      relevanceScore: 0.93,
      reason: 'Historical failure mode that justifies stale-state guardrails and runbook linkage.',
    },
    {
      evidenceId: 'evidence-pr-502',
      title: 'PR-502 Add Execution Status Polling',
      sourcePath: 'knowledge_packs/demo_team/docs/historical-pr/PR-502-add-execution-status-polling.md',
      sourceType: 'historical_pr',
      excerpt: 'Reviewer noted backend status updates were present but UI stale polling states needed follow-up.',
      relevanceScore: 0.88,
      reason: 'Shows frontend review concern and expected PR review question.',
    },
    {
      evidenceId: 'evidence-status-tracker',
      title: 'StatusTracker.java',
      sourcePath: 'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java',
      sourceType: 'code_file',
      excerpt: 'Persists authoritative execution and task status transitions to prevent stale RUNNING state.',
      relevanceScore: 0.9,
      reason: 'Maps the requirement to backend implementation ownership.',
    },
    {
      evidenceId: 'evidence-test-plan',
      title: 'Status Transition Test Plan',
      sourcePath: 'knowledge_packs/demo_team/docs/testing/status-transition-test-plan.md',
      sourceType: 'testing_doc',
      excerpt: 'Regression tests cover queued, running, failed, completed, cancelled, partial success, and stuck RUNNING recovery paths.',
      relevanceScore: 0.87,
      reason: 'Anchors acceptance criteria and required regression coverage.',
    },
    {
      evidenceId: 'evidence-inc-105',
      title: 'INC-105 Partial Completion Undefined',
      sourcePath: 'knowledge_packs/demo_team/docs/incidents/INC-105-partial-completion-undefined.md',
      sourceType: 'incident',
      excerpt: 'One task failed while other tasks completed; partial success and partial result availability were not defined.',
      relevanceScore: 0.8,
      reason: 'Triggers explicit product clarification instead of assumed behavior.',
    },
    {
      evidenceId: 'evidence-execution-monitor',
      title: 'ExecutionMonitorComponent',
      sourcePath: 'examples/dfp-demo-repo/frontend/src/app/execution/execution-monitor.component.ts',
      sourceType: 'code_file',
      excerpt: 'Renders job and task status, polling state, stale data warnings, and operator-facing retry hints.',
      relevanceScore: 0.84,
      reason: 'Maps context to the Angular surface likely affected by the requirement.',
    },
  ],
  logicChain: [
    {
      id: 'logic-intent',
      order: 1,
      title: 'Intent extraction',
      input: 'Rough request mentions long forecast jobs and uncertainty about the running task.',
      output: 'Normalize to async execution status, task progress, stale polling, and review questions.',
      evidenceIds: ['evidence-dfp-101', 'evidence-status-design'],
      status: 'pass',
    },
    {
      id: 'logic-grounding',
      order: 2,
      title: 'Evidence grounding',
      input: 'Search knowledge chunks and graph paths for execution status and stuck RUNNING.',
      output: 'Select architecture, incident, PR, testing, and code evidence with source paths.',
      evidenceIds: ['evidence-status-design', 'evidence-inc-103', 'evidence-pr-502'],
      status: 'pass',
    },
    {
      id: 'logic-impact',
      order: 3,
      title: 'Impact mapping',
      input: 'Bind source evidence to frontend, backend, API, test, and Ops ownership.',
      output: 'Produce component impact map and role-specific clarification questions.',
      evidenceIds: ['evidence-execution-monitor', 'evidence-status-tracker', 'evidence-test-plan'],
      status: 'pass',
    },
    {
      id: 'logic-ambiguity',
      order: 4,
      title: 'Ambiguity handling',
      input: 'Partial success behavior appears in incidents but lacks final product decision.',
      output: 'Mark partial output availability and timeout threshold as needs_review.',
      evidenceIds: ['evidence-inc-105', 'evidence-test-plan'],
      status: 'watch',
    },
    {
      id: 'logic-prompt',
      order: 5,
      title: 'Prompt assembly',
      input: 'Combine request interpretation, evidence bundle, impact lens, and guardrails.',
      output: 'Prepare draft-only prompt preview for requirement case generation.',
      evidenceIds: ['evidence-status-design', 'evidence-inc-103', 'evidence-pr-502', 'evidence-test-plan'],
      status: 'pass',
    },
  ],
};

const MOCK_REQUIREMENT_CASES: RequirementCase[] = [
  buildRequirementCase({
    rawRequest: 'Users want to know which task is still running when a forecast job takes too long.',
    role: 'BA',
    sources: MOCK_CHUNKS.slice(0, 7),
    codeEvidence: MOCK_CODEBASE_FILES.slice(0, 6),
  }),
];

const MOCK_SCORECARDS: EvaluationScorecard[] = [
  createScorecard({
    targetType: 'engineering_brief',
    targetId: MOCK_REQUIREMENT_CASES[0].caseId,
    overallScore: 8.7,
    sourcePaths: [
      ...MOCK_CHUNKS.slice(0, 7).map((chunk) => chunk.sourcePath),
      ...MOCK_CODEBASE_FILES.slice(0, 6).map((file) => file.path),
    ],
    recommendations: [
      'Confirm UI polling interval before ticket grooming.',
      'Add explicit partial completion acceptance criteria.',
    ],
  }),
];

const MOCK_AUDIT_RUNS: AuditRun[] = [
  {
    runId: 'run_20260620_0042',
    useCase: 'eval_scorecard',
    teamId: 'demo_team',
    app: 'ForecastDemo',
    status: 'completed',
    startedAt: '2026-06-20T17:18:00.000Z',
    duration: '00:00:31',
    modelProvider: 'deterministic-eval',
    modelName: 'rule-based-scorecard-v1',
    outputPath: 'artifacts/evals/eval_async_status_tracking.md',
    warnings: [],
    sourcesUsed: ['knowledge_packs/demo_team/eval_profiles/async-status-tracking.yaml'],
  },
  {
    runId: 'run_20260620_0041',
    useCase: 'engineering_brief',
    teamId: 'demo_team',
    app: 'ForecastDemo',
    status: 'needs_review',
    startedAt: '2026-06-20T17:12:00.000Z',
    duration: '00:01:52',
    modelProvider: 'mock-llm',
    modelName: 'mock-deterministic-v1',
    outputPath: 'artifacts/requirement-cases/case_async_status/engineering-brief.md',
    warnings: ['Clarify polling interval and stuck RUNNING timeout.'],
    sourcesUsed: [
      'knowledge_packs/demo_team/docs/architecture/status-tracking-design.md',
      'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/execution/StatusTracker.java',
    ],
  },
  {
    runId: 'run_20260620_0040',
    useCase: 'pr_review_summary',
    teamId: 'demo_team',
    app: 'OutputPreviewDemo',
    status: 'needs_review',
    startedAt: '2026-06-20T16:45:00.000Z',
    duration: '00:02:08',
    modelProvider: 'mock-llm',
    modelName: 'mock-deterministic-v1',
    outputPath: 'artifacts/pr-review-summary-DFP-110.md',
    warnings: ['Human review required before PR comment posting.'],
    sourcesUsed: [
      'knowledge_packs/demo_team/docs/incidents/INC-102-duplicate-output.md',
      'examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java',
    ],
  },
  {
    runId: 'run_20260620_0039',
    useCase: 'codebase_index',
    teamId: 'demo_team',
    app: 'ForecastDemo',
    status: 'completed',
    startedAt: '2026-06-20T16:18:00.000Z',
    duration: '00:00:18',
    modelProvider: 'local-indexer',
    modelName: 'structured-keyword-index-v1',
    outputPath: 'artifacts/codebase-indexes/demo_team/dfp-demo-repo.json',
    warnings: [],
    sourcesUsed: ['examples/dfp-demo-repo'],
  },
  {
    runId: 'run_20260620_0038',
    useCase: 'testgen_stub',
    teamId: 'demo_team',
    app: 'BatchJobDemo',
    status: 'stub_only',
    startedAt: '2026-06-20T16:02:00.000Z',
    duration: '00:00:21',
    modelProvider: 'mock-testgen',
    modelName: 'mock-testgen-v1',
    outputPath: 'artifacts/testgen-stub-run_20260620_0038.md',
    warnings: ['No unit-test generation engine was executed.'],
    sourcesUsed: [],
  },
];

const MOCK_RATINGS: HumanRating[] = [
  {
    runId: 'run_20260620_0041',
    usefulnessScore: 4,
    correctnessScore: 4,
    comments: 'Good engineering brief. Needs final BA decision on timeout threshold and status labels.',
    createdAt: '2026-06-20T17:30:00.000Z',
  },
];
