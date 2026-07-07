// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';

import { AuditRun, EvaluationScorecard, RequirementCase, RunStatus } from '../../core/dream-models';
import {
  CodebaseIndexFile,
  DreamApiService,
  IntakeDocument,
} from '../../core/dream-api.service';
import { UiIconComponent } from '../../shared/ui-icon.component';

interface DashboardMetric {
  label: string;
  value: number | string;
  note: string;
  tone: 'info' | 'warning' | 'success' | 'neutral';
  variant: 'sources' | 'jira' | 'pr' | 'approved';
}

interface WorkQueueItem {
  id: string;
  type: string;
  title: string;
  status: string;
  route: string;
  note: string;
  meta: string;
  tone: 'info' | 'warning' | 'success' | 'neutral';
  actionLabel: string;
}

interface StartAction {
  label: string;
  summary: string;
  route: string;
  icon: 'document' | 'clipboard' | 'code' | 'database';
  tone: 'primary' | 'neutral';
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, UiIconComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  private readonly api = inject(DreamApiService);
  private readonly dateFormatter = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  readonly isLoading = signal(false);
  readonly apiError = signal<string | null>(null);
  readonly intakeDocuments = signal<IntakeDocument[]>([]);
  readonly codebaseFiles = signal<CodebaseIndexFile[]>([]);
  readonly requirementCases = signal<RequirementCase[]>([]);
  readonly auditRuns = signal<AuditRun[]>([]);
  readonly scorecards = signal<EvaluationScorecard[]>([]);

  readonly sourceReviewQueue = computed(() =>
    this.intakeDocuments().filter((document) => this.sourceNeedsReview(document)),
  );
  readonly approvedSourceItems = computed(() =>
    this.intakeDocuments().filter((document) => this.sourceApproved(document)),
  );
  readonly latestRequirementCases = computed(() =>
    latestRequirementCasesByIdentity(this.requirementCases()),
  );
  readonly jiraDraftsNeedReview = computed(() =>
    this.latestRequirementCases().filter((requirementCase) => !this.requirementApproved(requirementCase)),
  );
  readonly approvedJiraDrafts = computed(() =>
    this.latestRequirementCases().filter((requirementCase) => this.requirementApproved(requirementCase)),
  );
  readonly prReviewRuns = computed(() =>
    this.auditRuns().filter((run) => run.useCase === 'pr_review_summary'),
  );
  readonly prReviewsNeedReview = computed(() =>
    this.prReviewRuns().filter((run) => !this.runApproved(run.status)),
  );
  readonly approvedPrReviews = computed(() =>
    this.prReviewRuns().filter((run) => this.runApproved(run.status)),
  );
  readonly latestScorecards = computed(() => latestScorecardsByTarget(this.scorecards()));
  readonly evalsNeedReview = computed(() =>
    this.latestScorecards().filter((scorecard) => scorecard.passStatus !== 'pass'),
  );

  readonly summaryMetrics = computed<DashboardMetric[]>(() => [
    {
      label: 'Docs in Memory',
      value: this.approvedSourceItems().length,
      note: `${this.intakeDocuments().length} source records from FastAPI`,
      tone: this.approvedSourceItems().length ? 'info' : 'neutral',
      variant: 'sources',
    },
    {
      label: 'Docs Need Review',
      value: this.sourceReviewQueue().length,
      note: `${this.approvedSourceItems().length} already promoted`,
      tone: this.sourceReviewQueue().length ? 'warning' : 'success',
      variant: 'sources',
    },
    {
      label: 'Jira Drafts',
      value: this.jiraDraftsNeedReview().length,
      note: `${this.requirementCases().length} raw records / ${this.approvedJiraDrafts().length} ready`,
      tone: this.jiraDraftsNeedReview().length ? 'warning' : 'success',
      variant: 'jira',
    },
    {
      label: 'PR Reviews',
      value: this.prReviewsNeedReview().length,
      note: `${this.approvedPrReviews().length} generated successfully`,
      tone: this.prReviewsNeedReview().length ? 'warning' : 'success',
      variant: 'pr',
    },
  ]);

  readonly workQueue = computed<WorkQueueItem[]>(() => [
    ...this.sourceReviewQueue().map((document) => ({
      id: document.documentId,
      type: 'Source Doc',
      title: document.title,
      status: this.statusLabel(document.status),
      route: '/memory',
      note: `Structured intake record from ${document.documentType}.`,
      meta: `${document.teamId} / ${this.shortDate(document.updatedAt)}`,
      tone: 'warning' as const,
      actionLabel: 'Open memory',
    })),
    ...this.jiraDraftsNeedReview().map((requirementCase) => ({
      id: requirementCase.caseId,
      type: 'Jira Draft',
      title: requirementCase.title,
      status: this.statusLabel(requirementCase.jiraReadinessStatus || requirementCase.status),
      route: '/requirements',
      note: `${this.openQuestionCount(requirementCase)} open questions before handoff.`,
      meta: `${requirementCase.createdByRole} / ${this.shortDate(requirementCase.updatedAt)}`,
      tone: 'warning' as const,
      actionLabel: 'Open workbench',
    })),
    ...this.prReviewsNeedReview().map((run) => ({
      id: run.runId,
      type: 'PR Review',
      title: this.outputTitleFromRun(run),
      status: this.statusLabel(run.status),
      route: '/review',
      note: run.warnings[0] || 'Generated review should be checked by a human reviewer.',
      meta: `${run.app} / ${this.shortDate(run.startedAt)}`,
      tone: 'warning' as const,
      actionLabel: 'Open workbench',
    })),
    ...this.evalsNeedReview().slice(0, 4).map((scorecard) => ({
      id: scorecard.evaluationId,
      type: 'Eval',
      title: `${this.statusLabel(scorecard.targetType)} / Grade ${scorecard.grade}`,
      status: this.statusLabel(scorecard.passStatus),
      route: `/audit/${scorecard.evaluationId}`,
      note: scorecard.recommendations[0] || 'Eval agent has review notes.',
      meta: `${scorecard.overallScore}/10`,
      tone: 'warning' as const,
      actionLabel: 'View eval',
    })),
  ]);

  readonly startActions: StartAction[] = [
    {
      label: 'Source Intake',
      summary: 'Review real source records already registered in FastAPI.',
      route: '/memory',
      icon: 'document',
      tone: 'primary',
    },
    {
      label: 'Draft Jira',
      summary: 'Generate a Jira proposal through the live requirement case workflow.',
      route: '/requirements',
      icon: 'clipboard',
      tone: 'neutral',
    },
    {
      label: 'Review PR',
      summary: 'Run PR review through FastAPI and open Eval Agent details.',
      route: '/review',
      icon: 'code',
      tone: 'neutral',
    },
    {
      label: 'Open Codebase',
      summary: 'Inspect the real repo index and code-to-concept evidence.',
      route: '/codebase',
      icon: 'database',
      tone: 'neutral',
    },
  ];

  constructor() {
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.isLoading.set(true);
    this.apiError.set(null);
    forkJoin({
      intakeDocuments: this.api.listIntakeDocuments().pipe(catchError(() => of([]))),
      codebaseFiles: this.api.listCodebaseFiles('demo_team', 'dfp-demo-repo').pipe(catchError(() => of([]))),
      requirementCases: this.api.listRequirementCases().pipe(catchError(() => of([]))),
      auditRuns: this.api.listAuditRuns('DREAM').pipe(catchError(() => of([]))),
      scorecards: this.api.listEvaluationRuns().pipe(catchError(() => of([]))),
    }).subscribe({
      next: ({ intakeDocuments, codebaseFiles, requirementCases, auditRuns, scorecards }) => {
        this.intakeDocuments.set(intakeDocuments);
        this.codebaseFiles.set(codebaseFiles);
        this.requirementCases.set(requirementCases);
        this.auditRuns.set(auditRuns);
        this.scorecards.set(scorecards);
        this.isLoading.set(false);
      },
      error: () => {
        this.apiError.set('FastAPI data could not be loaded.');
        this.isLoading.set(false);
      },
    });
  }

  shortDate(value: string): string {
    return this.dateFormatter.format(new Date(value));
  }

  statusLabel(value: string): string {
    return value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private sourceNeedsReview(document: IntakeDocument): boolean {
    return !this.sourceApproved(document);
  }

  private sourceApproved(document: IntakeDocument): boolean {
    return document.status === 'promoted';
  }

  private requirementApproved(requirementCase: RequirementCase): boolean {
    return Boolean(requirementCase.jiraReady || requirementCase.status === 'jira_ready_draft');
  }

  private runApproved(status: RunStatus): boolean {
    return status === 'completed' || status === 'success' || status === 'pass';
  }

  private openQuestionCount(requirementCase: RequirementCase): number {
    return requirementCase.questions.filter((question) => question.status === 'open').length;
  }

  private outputTitleFromRun(run: AuditRun): string {
    const filename = run.outputPath.split('/').at(-1) || run.runId;
    return filename.replace(/\.md$/i, '').replace(/[-_]/g, ' ');
  }
}

function latestRequirementCasesByIdentity(cases: RequirementCase[]): RequirementCase[] {
  const latestByKey = new Map<string, RequirementCase>();
  for (const requirementCase of cases) {
    const key = requirementIdentityKey(requirementCase);
    const existing = latestByKey.get(key);
    if (!existing || timestamp(requirementCase.updatedAt) > timestamp(existing.updatedAt)) {
      latestByKey.set(key, requirementCase);
    }
  }
  return [...latestByKey.values()].sort(
    (left, right) => timestamp(right.updatedAt) - timestamp(left.updatedAt),
  );
}

function requirementIdentityKey(requirementCase: RequirementCase): string {
  return [
    requirementCase.createdByRole,
    requirementCase.title,
    requirementCase.rawRequest,
  ]
    .map((part) => normalizeIdentityPart(part || ''))
    .join('|');
}

function normalizeIdentityPart(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function timestamp(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function latestScorecardsByTarget(scorecards: EvaluationScorecard[]): EvaluationScorecard[] {
  const latestByKey = new Map<string, EvaluationScorecard>();
  for (const scorecard of scorecards) {
    const key = scorecardTargetKey(scorecard);
    if (!latestByKey.has(key)) {
      latestByKey.set(key, scorecard);
    }
  }
  return [...latestByKey.values()];
}

function scorecardTargetKey(scorecard: EvaluationScorecard): string {
  const target =
    scorecard.targetId && scorecard.targetId !== scorecard.evaluationId
      ? scorecard.targetId
      : scorecard.caseId || scorecard.outputPath || scorecard.evaluationId;
  return [
    scorecard.targetType,
    target,
  ]
    .map((part) => normalizeIdentityPart(part || ''))
    .join('|');
}
