// SPDX-License-Identifier: Apache-2.0

import { KeyValuePipe } from '@angular/common';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { catchError, forkJoin, map, of } from 'rxjs';

import {
  AuditRun,
  EvaluationDimension,
  EvaluationScorecard,
  HumanRating,
  RequirementCase,
} from '../../core/dream-models';
import { DreamApiService, IntakeDocument } from '../../core/dream-api.service';
import { sourceDocumentRoute as routeForSourceDocument } from '../../core/source-provenance';

interface ScoringStandard {
  label: string;
  rule: string;
  note: string;
}

@Component({
  selector: 'app-audit-eval',
  standalone: true,
  imports: [KeyValuePipe, ReactiveFormsModule, RouterLink],
  templateUrl: './audit-eval.component.html',
  styleUrl: './audit-eval.component.scss',
})
export class AuditEvalComponent {
  private readonly api = inject(DreamApiService);
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly runs = signal<AuditRun[]>([]);
  readonly ratings = signal<HumanRating[]>([]);
  readonly ratingsRunId = signal<string | null>(null);
  readonly ratingInFlight = signal(false);
  readonly scorecards = signal<EvaluationScorecard[]>([]);
  readonly requirementCases = signal<RequirementCase[]>([]);
  readonly intakeDocuments = signal<IntakeDocument[]>([]);
  readonly apiScorecard = signal<EvaluationScorecard | null>(null);
  readonly apiRun = signal<AuditRun | null>(null);
  readonly apiRequirementCase = signal<RequirementCase | null>(null);
  readonly apiError = signal<string | null>(null);
  readonly scorePage = signal(1);
  readonly auditPage = signal(1);
  readonly scorePageSize = 9;
  readonly auditPageSize = 10;
  readonly selectedRunId = signal<string | null>(this.route.snapshot.paramMap.get('targetId'));
  readonly targetId = toSignal(
    this.route.paramMap.pipe(map((params) => params.get('targetId'))),
    { initialValue: this.route.snapshot.paramMap.get('targetId') },
  );

  readonly scoringStandards: ScoringStandard[] = [
    {
      label: 'Overall score',
      rule: 'Weighted average of eval dimensions on a 0-10 scale.',
      note: 'Current local rule gives each dimension equal weight.',
    },
    {
      label: 'Pass gate',
      rule: 'Pass >= 7.0, warning 5.5-6.9, fail < 5.5.',
      note: 'Generated output still requires human review before handoff.',
    },
    {
      label: 'Grade bands',
      rule: 'A >= 8.5, B >= 7.0, C >= 5.5, D >= 4.0, F < 4.0.',
      note: 'Grade summarizes confidence; it does not approve release.',
    },
    {
      label: 'Dimension pass',
      rule: 'Each dimension passes when its score is >= 7.0.',
      note: 'Failed dimensions expose missing items and recommendations.',
    },
  ];

  readonly visibleScorecards = computed(() => {
    const apiScorecard = this.apiScorecard();
    const cards = this.scorecards();
    if (!apiScorecard || cards.some((card) => card.evaluationId === apiScorecard.evaluationId)) {
      return cards;
    }
    return [apiScorecard, ...cards];
  });

  readonly visibleRuns = computed(() => {
    const apiRun = this.apiRun();
    const runs = this.runs();
    if (!apiRun || runs.some((run) => run.runId === apiRun.runId)) {
      return runs;
    }
    return [apiRun, ...runs];
  });

  readonly isDetailRoute = computed(() => Boolean(this.targetId()));
  readonly totalScorePages = computed(() =>
    Math.max(1, Math.ceil(this.visibleScorecards().length / this.scorePageSize)),
  );
  readonly pagedScorecards = computed(() => {
    const start = (this.scorePage() - 1) * this.scorePageSize;
    return this.visibleScorecards().slice(start, start + this.scorePageSize);
  });
  readonly totalAuditPages = computed(() =>
    Math.max(1, Math.ceil(this.visibleRuns().length / this.auditPageSize)),
  );
  readonly pagedRuns = computed(() => {
    const start = (this.auditPage() - 1) * this.auditPageSize;
    return this.visibleRuns().slice(start, start + this.auditPageSize);
  });

  readonly selectedScorecard = computed(() => {
    const targetId = this.targetId();
    const selectedRunId = this.selectedRunId();
    if (!targetId && !selectedRunId) {
      return null;
    }
    return (
      this.apiScorecard() ??
      this.scorecards().find(
        (card) => card.targetId === targetId || card.evaluationId === targetId,
      ) ??
      this.scorecards().find(
        (card) => card.targetId === selectedRunId || card.evaluationId === selectedRunId,
      ) ??
      this.scorecards()[0] ??
      null
    );
  });

  readonly selectedRun = computed<AuditRun | null>(() => {
    const explicitRunId = this.selectedRunId();
    const targetId = this.targetId();
    const scorecard = this.selectedScorecard();
    if (!explicitRunId && !targetId && !scorecard) {
      return null;
    }
    return (
      this.apiRun() ??
      this.runs().find((run) => run.runId === explicitRunId) ??
      this.runs().find((run) => run.runId === targetId) ??
      this.runs().find((run) => run.runId === scorecard?.evaluationId) ??
      this.runs().find((run) => run.runId === scorecard?.runId) ??
      this.runs().find((run) => run.caseId === scorecard?.caseId) ??
      this.runs().find((run) => run.runId === scorecard?.targetId) ??
      this.runs().find((run) => scorecard?.targetId && run.outputPath.includes(scorecard.targetId)) ??
      this.runs()[0] ??
      null
    );
  });

  readonly selectedRequirementCase = computed(() => {
    const targetId = this.targetId();
    const scorecard = this.selectedScorecard();
    return (
      this.apiRequirementCase() ??
      this.requirementCases().find(
        (requirementCase) =>
          requirementCase.caseId === targetId ||
          requirementCase.caseId === scorecard?.targetId ||
          requirementCase.caseId === scorecard?.caseId,
      ) ?? null
    );
  });

  readonly selectedDimensions = computed(() => this.selectedScorecard()?.dimensions ?? []);
  readonly selectedRatings = computed(() =>
    this.ratings().filter((rating) => rating.runId === this.selectedRun()?.runId),
  );

  readonly ratingForm = this.fb.nonNullable.group({
    usefulnessScore: [4, [Validators.required, Validators.min(1), Validators.max(5)]],
    correctnessScore: [4, [Validators.required, Validators.min(1), Validators.max(5)]],
    comments: ['Useful output; needs human review before handoff.', Validators.required],
  });

  constructor() {
    this.loadApiLists();
    effect(() => {
      this.loadApiDetail(this.targetId());
    });
    effect(() => {
      const runId = this.selectedRun()?.runId ?? null;
      if (!runId) {
        this.ratings.set([]);
        this.ratingsRunId.set(null);
        return;
      }
      if (this.ratingsRunId() !== runId) {
        this.loadRatings(runId);
      }
    });
  }

  selectRun(run: AuditRun): void {
    this.selectedRunId.set(run.runId);
  }

  previousScorePage(): void {
    this.scorePage.update((page) => Math.max(1, page - 1));
  }

  nextScorePage(): void {
    this.scorePage.update((page) => Math.min(this.totalScorePages(), page + 1));
  }

  previousAuditPage(): void {
    this.auditPage.update((page) => Math.max(1, page - 1));
  }

  nextAuditPage(): void {
    this.auditPage.update((page) => Math.min(this.totalAuditPages(), page + 1));
  }

  isSelectedScorecard(scorecard: EvaluationScorecard): boolean {
    return this.selectedScorecard()?.evaluationId === scorecard.evaluationId;
  }

  openScorecard(scorecard: EvaluationScorecard, event: Event): void {
    event.preventDefault();
    this.apiScorecard.set(scorecard);
    this.apiRun.set(null);
    this.apiRequirementCase.set(null);
    this.apiError.set(null);
    this.selectedRunId.set(scorecard.evaluationId);
    this.loadApiRun(scorecard);
    if (scorecard.caseId || scorecard.targetId.startsWith('case-')) {
      this.loadApiRequirementCase(scorecard.caseId || scorecard.targetId);
    }
    void this.router.navigate(['/audit', scorecard.evaluationId]);
    window.setTimeout(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  openEvalList(event: Event): void {
    event.preventDefault();
    this.apiScorecard.set(null);
    this.apiRun.set(null);
    this.apiRequirementCase.set(null);
    this.selectedRunId.set(null);
    void this.router.navigate(['/audit']);
    window.setTimeout(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  submitRating(): void {
    const run = this.selectedRun();
    if (!run || this.ratingForm.invalid) {
      this.ratingForm.markAllAsTouched();
      return;
    }
    this.ratingInFlight.set(true);
    this.apiError.set(null);
    const value = this.ratingForm.getRawValue();
    this.api
      .rateAuditRun({
        runId: run.runId,
        usefulnessScore: value.usefulnessScore,
        correctnessScore: value.correctnessScore,
        comments: value.comments,
      })
      .subscribe({
        next: (rating) => {
          this.ratingsRunId.set(run.runId);
          this.ratings.update((ratings) => [
            rating,
            ...ratings.filter((item) => item.createdAt !== rating.createdAt),
          ]);
          this.ratingInFlight.set(false);
        },
        error: () => {
          this.apiError.set('Could not persist the human rating.');
          this.ratingInFlight.set(false);
        },
      });
  }

  loadApiLists(): void {
    this.apiError.set(null);
    forkJoin({
      runs: this.api.listAuditRuns('DREAM').pipe(catchError(() => of([]))),
      scorecards: this.api.listEvaluationRuns().pipe(catchError(() => of([]))),
      requirementCases: this.api.listRequirementCases().pipe(catchError(() => of([]))),
      intakeDocuments: this.api.listIntakeDocuments().pipe(catchError(() => of([]))),
    }).subscribe({
      next: ({ runs, scorecards, requirementCases, intakeDocuments }) => {
        this.runs.set(runs);
        this.scorecards.set(scorecards);
        this.requirementCases.set(requirementCases);
        this.intakeDocuments.set(intakeDocuments);
      },
      error: () => {
        this.apiError.set('Could not load FastAPI audit and eval data.');
      },
    });
  }

  dimensionStatusClass(dimension: EvaluationDimension): string {
    return dimension.passed ? 'status-success' : 'status-warning';
  }

  formatLabel(value: string): string {
    return value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  scoreBand(score: number): string {
    if (score >= 8.5) {
      return 'A band';
    }
    if (score >= 7) {
      return 'B band';
    }
    if (score >= 5.5) {
      return 'Warning band';
    }
    return 'Fail band';
  }

  coverageStatus(value: boolean): string {
    return value ? 'Covered' : 'Missing';
  }

  coverageStatusClass(value: boolean): string {
    return value ? 'status-success' : 'status-warning';
  }

  coverageCount(scorecard: EvaluationScorecard): number {
    return Object.keys(scorecard.sourceCoverage).length;
  }

  failedDimensionCount(scorecard: EvaluationScorecard): number {
    return scorecard.dimensions.filter((dimension) => !dimension.passed).length;
  }

  missingItemCount(scorecard: EvaluationScorecard): number {
    const dimensionMissing = scorecard.dimensions.reduce(
      (count, dimension) => count + dimension.missingItems.length,
      0,
    );
    return dimensionMissing + scorecard.missingCriticalItems.length;
  }

  recommendationCount(scorecard: EvaluationScorecard): number {
    return scorecard.recommendations.length;
  }

  cardReviewHint(scorecard: EvaluationScorecard): string {
    if (scorecard.passStatus === 'pass') {
      return 'Passed eval gate. Open only for audit trail or handoff evidence.';
    }
    if (scorecard.missingCriticalItems.length) {
      return 'Critical gaps found. Open detail before handoff.';
    }
    if (this.failedDimensionCount(scorecard)) {
      return 'Some dimensions need review. Open detail for rationale.';
    }
    return 'Review recommended before final approval.';
  }

  openQuestionCount(requirementCase: RequirementCase): number {
    return requirementCase.questions.filter((question) => question.status === 'open').length;
  }

  contextCaseId(scorecard: EvaluationScorecard): string | null {
    return scorecard.caseId || (scorecard.targetId.startsWith('case-') ? scorecard.targetId : null);
  }

  sourceFileName(sourcePath: string): string {
    const normalized = sourcePath.split('#')[0];
    return normalized.split('/').pop() || sourcePath;
  }

  sourceDocumentRoute(sourcePath: string): string[] | null {
    return routeForSourceDocument(sourcePath, this.intakeDocuments());
  }

  private loadApiDetail(targetId: string | null): void {
    this.apiRun.set(null);
    this.apiRequirementCase.set(null);
    if (!targetId) {
      this.apiScorecard.set(null);
      this.selectedRunId.set(null);
      return;
    }
    if (!targetId || (!targetId.startsWith('eval-') && !targetId.startsWith('case-'))) {
      return;
    }
    this.apiError.set(null);
    if (targetId.startsWith('eval-')) {
      this.api.getEvaluationRun(targetId).subscribe({
        next: (scorecard) => {
          this.apiScorecard.set(scorecard);
          this.selectedRunId.set(scorecard.evaluationId);
          this.loadApiRun(scorecard);
          const caseId = scorecard.caseId || (scorecard.targetId.startsWith('case-') ? scorecard.targetId : null);
          if (caseId) {
            this.loadApiRequirementCase(caseId);
          } else {
            this.apiRequirementCase.set(null);
          }
        },
        error: () => {
          this.apiError.set('Could not load the eval run from FastAPI.');
        },
      });
      return;
    }
    this.loadApiRequirementCase(targetId);
  }

  private loadApiRun(scorecard: EvaluationScorecard): void {
    this.api.listAuditRuns(scorecard.teamId || 'Demo').subscribe({
      next: (runs) => {
        this.apiRun.set(
          runs.find((run) => run.runId === scorecard.evaluationId) ??
            runs.find((run) => run.runId === scorecard.runId) ??
            runs.find((run) => run.caseId === scorecard.caseId && run.useCase === 'evaluation_scorecard') ??
            runs.find((run) => run.caseId === scorecard.caseId && run.useCase === 'jira_draft') ??
            null,
        );
      },
      error: () => {
        this.apiRun.set(null);
      },
    });
  }

  private loadApiRequirementCase(caseId: string): void {
    this.api.getRequirementCase(caseId).subscribe({
      next: (requirementCase) => this.apiRequirementCase.set(requirementCase),
      error: () => this.apiRequirementCase.set(null),
    });
  }

  private loadRatings(runId: string): void {
    this.api.listHumanRatings(runId).subscribe({
      next: (ratings) => {
        this.ratingsRunId.set(runId);
        this.ratings.set(ratings);
      },
      error: () => {
        this.ratingsRunId.set(runId);
        this.ratings.set([]);
      },
    });
  }
}
