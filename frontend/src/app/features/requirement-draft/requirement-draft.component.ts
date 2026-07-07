// SPDX-License-Identifier: Apache-2.0

import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ClarificationQuestion, RequirementDraftInput, RequirementDraftResult } from '../../core/dream-models';
import {
  DreamApiService,
  RequirementDraftLifecycleProgress,
} from '../../core/dream-api.service';
import type { IntakeDocument } from '../../core/dream-api.service';
import { sourceDocumentRoute as routeForSourceDocument } from '../../core/source-provenance';
import { UiIconComponent } from '../../shared/ui-icon.component';
import {
  RequirementLifecycleProgressComponent,
  RequirementLifecycleState,
  RequirementLifecycleStep,
} from './requirement-lifecycle-progress.component';
import {
  JiraProposalReferenceLink,
  JiraProposalViewComponent,
} from './jira-proposal-view.component';

interface AffectedFileView {
  path: string;
  areaType: string;
  reason: string;
}

interface QuestionWaiverDraft {
  reason: string;
  note: string;
}

@Component({
  selector: 'app-requirement-draft',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    UiIconComponent,
    RequirementLifecycleProgressComponent,
    JiraProposalViewComponent,
  ],
  templateUrl: './requirement-draft.component.html',
  styleUrl: './requirement-draft.component.scss',
})
export class RequirementDraftComponent {
  private readonly api = inject(DreamApiService);
  private readonly fb = inject(FormBuilder);

  readonly apps = ['ForecastDemo', 'BatchJobDemo', 'OutputPreviewDemo'];
  readonly result = signal<RequirementDraftResult | null>(null);
  readonly isLoading = signal(false);
  readonly apiError = signal<string | null>(null);
  readonly questionAnswers = signal<Record<string, string>>({});
  readonly questionWaivers = signal<Record<string, QuestionWaiverDraft>>({});
  readonly activeQuestionId = signal<string | null>(null);
  readonly advancedOpen = signal(false);
  readonly impactDetailsOpen = signal(false);
  readonly intakeDocuments = signal<IntakeDocument[]>([]);
  readonly lifecycleState = signal<RequirementLifecycleState>('idle');
  readonly lifecycleStepIndex = signal(-1);
  readonly lifecycleDurations = signal<Record<string, number>>({});
  readonly lifecycleButtonLabel = computed(() => {
    const step = this.lifecycleSteps[this.lifecycleStepIndex()];
    return step?.runningLabel ?? 'Running lifecycle...';
  });

  readonly lifecycleSteps: RequirementLifecycleStep[] = [
    {
      id: 'create_analyze_phase',
      label: 'Create & analyze',
      detail: 'Create the case, retrieve memory, bind codebase, map impact, and open questions.',
      runningLabel: 'Analyzing request...',
    },
    {
      id: 'draft_jira_phase',
      label: 'Draft Jira',
      detail: 'Prepare prompt context, compose the proposal, and check readiness.',
      runningLabel: 'Drafting Jira...',
    },
    {
      id: 'eval_phase',
      label: 'Evaluate & load',
      detail: 'Run rubric score, LLM judge, and load final artifacts.',
      runningLabel: 'Evaluating result...',
    },
  ];
  readonly waiverReasons = [
    'Out of scope for this release',
    'Already covered by accepted criteria',
    'Duplicate of another question',
    'Accepted risk for demo handoff',
  ];

  readonly form = this.fb.nonNullable.group({
    executionMode: ['openai', Validators.required],
    teamId: ['demo_team', Validators.required],
    app: ['ForecastDemo', Validators.required],
    component: ['job-execution', Validators.required],
    role: ['BA', Validators.required],
    roughBusinessRequest: [
      'Users want to know which task is still running when a forecast job takes too long. The execution page should show better progress.',
      Validators.required,
    ],
    topK: [5, [Validators.required, Validators.min(1), Validators.max(20)]],
  });

  constructor() {
    this.loadIntakeDocuments();
  }

  generate(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const input = this.requirementInput();
    this.apiError.set(null);
    this.isLoading.set(true);
    this.startLifecycleProgress();
    this.api.draftRequirementWithOpenAI(input, (progress) => this.applyLifecycleProgress(progress)).subscribe({
      next: (result) => {
        this.acceptDraftResult(result);
        this.completeLifecycleProgress();
        this.isLoading.set(false);
      },
      error: (error: unknown) => {
        this.apiError.set(this.errorMessage(error, 'OpenAI requirement case request failed.'));
        this.failLifecycleProgress();
        this.isLoading.set(false);
      },
    });
  }

  toggleAdvancedSettings(): void {
    this.advancedOpen.update((open) => !open);
  }

  toggleImpactDetails(): void {
    this.impactDetailsOpen.update((open) => !open);
  }

  updateQuestionAnswer(questionId: string, eventOrValue: Event | string): void {
    const value =
      typeof eventOrValue === 'string'
        ? eventOrValue
        : eventOrValue.target instanceof HTMLTextAreaElement
          ? eventOrValue.target.value
          : '';
    this.questionAnswers.update((answers) => ({ ...answers, [questionId]: value }));
  }

  saveQuestionAnswer(questionId: string): void {
    const current = this.result();
    const answer = this.questionAnswers()[questionId]?.trim();
    if (!current || !answer) {
      return;
    }
    this.apiError.set(null);
    this.activeQuestionId.set(questionId);
    this.api.answerRequirementQuestion(current.requirementCase.caseId, questionId, answer).subscribe({
      next: (updatedQuestion) => {
        this.result.set(this.withUpdatedQuestion(current, questionId, updatedQuestion));
        this.activeQuestionId.set(null);
      },
      error: (error: unknown) => {
        this.apiError.set(this.errorMessage(error, 'Failed to save answer to the API.'));
        this.activeQuestionId.set(null);
      },
    });
  }

  updateQuestionWaiverReason(questionId: string, eventOrValue: Event | string): void {
    const value =
      typeof eventOrValue === 'string'
        ? eventOrValue
        : eventOrValue.target instanceof HTMLSelectElement
          ? eventOrValue.target.value
          : this.waiverReasons[0];
    this.questionWaivers.update((waivers) => ({
      ...waivers,
      [questionId]: {
        reason: value || this.waiverReasons[0],
        note: waivers[questionId]?.note || '',
      },
    }));
  }

  updateQuestionWaiverNote(questionId: string, eventOrValue: Event | string): void {
    const value =
      typeof eventOrValue === 'string'
        ? eventOrValue
        : eventOrValue.target instanceof HTMLInputElement
          ? eventOrValue.target.value
          : '';
    this.questionWaivers.update((waivers) => ({
      ...waivers,
      [questionId]: {
        reason: waivers[questionId]?.reason || this.waiverReasons[0],
        note: value,
      },
    }));
  }

  waiveQuestion(questionId: string): void {
    const current = this.result();
    if (!current) {
      return;
    }
    const waiver = this.questionWaivers()[questionId] ?? {
      reason: this.waiverReasons[0],
      note: '',
    };
    const note = waiver.note.trim();
    const reason = note ? `${waiver.reason}: ${note}` : waiver.reason;
    if (!reason.trim()) {
      return;
    }
    this.apiError.set(null);
    this.activeQuestionId.set(questionId);
    this.api.waiveRequirementQuestion(current.requirementCase.caseId, questionId, reason).subscribe({
      next: (updatedQuestion) => {
        this.result.set(this.withUpdatedQuestion(current, questionId, updatedQuestion));
        this.questionAnswers.update((answers) => {
          const next = { ...answers };
          delete next[questionId];
          return next;
        });
        this.activeQuestionId.set(null);
      },
      error: (error: unknown) => {
        this.apiError.set(this.errorMessage(error, 'Failed to waive question in the API.'));
        this.activeQuestionId.set(null);
      },
    });
  }

  regenerateJiraDraft(): void {
    const current = this.result();
    if (!current) {
      return;
    }
    this.apiError.set(null);
    this.isLoading.set(true);
    this.startLifecycleProgress();
    this.api
      .regenerateRequirementCaseWithOpenAI(
        this.requirementInput(),
        current.requirementCase.caseId,
        (progress) => this.applyLifecycleProgress(progress),
      )
      .subscribe({
        next: (result) => {
          this.acceptDraftResult(result);
          this.completeLifecycleProgress();
          this.isLoading.set(false);
        },
        error: (error: unknown) => {
          this.apiError.set(this.errorMessage(error, 'Failed to regenerate Jira draft.'));
          this.failLifecycleProgress();
          this.isLoading.set(false);
        },
    });
  }

  readinessLabel(result: RequirementDraftResult): string {
    return result.requirementCase.jiraReady ? 'Jira ready' : 'Needs answers';
  }

  openQuestionCount(result: RequirementDraftResult): number {
    return result.requirementCase.questions.filter((question) => question.status === 'open').length;
  }

  affectedFiles(result: RequirementDraftResult): AffectedFileView[] {
    const byPath = new Map<string, AffectedFileView>();
    for (const impact of result.requirementCase.impactMap) {
      for (const source of impact.sources) {
        if (!this.isAffectedFileReference(impact.areaType, source)) {
          continue;
        }
        byPath.set(source, {
          path: source,
          areaType: impact.areaType,
          reason: impact.reason,
        });
      }
    }
    if (byPath.size) {
      return Array.from(byPath.values());
    }
    for (const evidence of result.requirementCase.evidence) {
      if (evidence.sourceType === 'code_file' || evidence.sourceType === 'test_file') {
        byPath.set(evidence.sourcePath, {
          path: evidence.sourcePath,
          areaType: this.sourceTypeLabel(evidence.sourceType),
          reason: evidence.reason,
        });
      }
    }
    return Array.from(byPath.values());
  }

  proposalAffectedFileLinks(result: RequirementDraftResult): JiraProposalReferenceLink[] {
    return this.affectedFiles(result).map((file) => ({
      label: this.fileName(file.path),
      detail: file.path,
      kind: this.proposalReferenceKind(file.path, file.areaType),
      route: ['/codebase'],
      queryParams: { file: file.path },
    }));
  }

  proposalSourceLinks(result: RequirementDraftResult): JiraProposalReferenceLink[] {
    return result.sourcesUsed.map((source) => {
      const memoryRoute = this.sourceDocumentRoute(source.sourcePath);
      const codeRoute = this.looksLikeCodeFileReference(source.sourcePath) ? ['/codebase'] : null;
      return {
        label: this.proposalReferenceLabel(source.sourcePath, source.title),
        detail: source.sourcePath,
        kind: this.proposalReferenceKind(source.sourcePath, this.sourceTypeLabel(source.sourceType)),
        route: memoryRoute ?? codeRoute,
        queryParams: memoryRoute ? null : codeRoute ? { file: source.sourcePath } : null,
      };
    });
  }

  matchedConcepts(result: RequirementDraftResult): string[] {
    return Array.from(new Set(result.sourcesUsed.flatMap((source) => source.concepts))).slice(0, 6);
  }

  sourceFamilies(result: RequirementDraftResult): Array<{ label: string; count: number }> {
    const counts = new Map<string, number>();
    for (const evidence of result.requirementCase.evidence) {
      const label = this.sourceTypeLabel(evidence.sourceType);
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    return Array.from(counts, ([label, count]) => ({ label, count }));
  }

  memoryMatchSummary(result: RequirementDraftResult): string {
    const families = [...this.sourceFamilies(result)].sort((a, b) => b.count - a.count);
    if (!families.length) {
      return 'No source families matched yet.';
    }
    const topFamilies = families
      .slice(0, 3)
      .map((family) => `${family.label} ${family.count}`)
      .join(', ');
    const extra = families.length > 3 ? `, +${families.length - 3} more` : '';
    return `${result.sourcesUsed.length} sources across ${families.length} families: ${topFamilies}${extra}.`;
  }

  impactAreas(result: RequirementDraftResult): string {
    return Array.from(new Set(result.requirementCase.impactMap.map((impact) => impact.areaType))).join(', ');
  }

  sourceTypeLabel(sourceType: string): string {
    return sourceType
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  fileName(path: string): string {
    return path.split('/').pop() || path;
  }

  proposalReferenceLabel(path: string, fallback: string): string {
    const conceptPrefix = '#concept:';
    const conceptIndex = path.indexOf(conceptPrefix);
    if (conceptIndex >= 0) {
      return path.slice(conceptIndex + conceptPrefix.length).trim() || fallback;
    }
    return this.fileName(path.split('#')[0]) || fallback;
  }

  proposalReferenceKind(path: string, fallback: string): string {
    if (path.includes('#concept:')) {
      return path.startsWith('evidence-graph') ? 'Graph evidence' : 'Concept';
    }
    if (/\.(java|ts|tsx|js|jsx|py|go|rb|cs|kt|scala)$/i.test(path)) {
      return /test|spec/i.test(path) ? 'Test file' : 'Code file';
    }
    return fallback;
  }

  sourceDocumentRoute(sourcePath: string): string[] | null {
    return routeForSourceDocument(sourcePath, this.intakeDocuments());
  }

  evalDecision(result: RequirementDraftResult): string {
    if (this.openQuestionCount(result) > 0) {
      return 'Needs review';
    }
    return result.scorecard.passStatus === 'pass' ? 'Ready for final approval' : 'Needs eval review';
  }

  workflowModeLabel(result: RequirementDraftResult): string {
    return 'Live FastAPI case lifecycle';
  }

  modelLabel(result: RequirementDraftResult): string {
    return `${result.run.modelProvider} / ${result.run.modelName}`;
  }

  llmJudgeState(result: RequirementDraftResult): 'success' | 'warning' | 'error' | 'idle' {
    const judge = result.scorecard.llmJudge;
    if (!judge) {
      return 'idle';
    }
    if (judge.status === 'failed') {
      return 'error';
    }
    return judge.readiness === 'ready' ? 'success' : 'warning';
  }

  llmJudgeStatusLabel(result: RequirementDraftResult): string {
    const judge = result.scorecard.llmJudge;
    if (!judge) {
      return 'LLM judge not requested';
    }
    if (judge.status === 'failed') {
      return 'LLM judge unavailable';
    }
    if (judge.readiness === 'ready') {
      return 'LLM judge ready';
    }
    if (judge.readiness === 'blocked') {
      return 'LLM judge blocked';
    }
    return 'LLM judge needs review';
  }

  llmJudgeMeta(result: RequirementDraftResult): string {
    const judge = result.scorecard.llmJudge;
    if (!judge) {
      return 'Optional model review was skipped.';
    }
    const parts = [
      judge.provider && judge.model ? `${judge.provider} / ${judge.model}` : undefined,
      judge.confidence !== undefined ? `confidence ${Math.round(judge.confidence * 100)}%` : undefined,
      judge.durationMs !== undefined ? this.durationLabel(judge.durationMs) : undefined,
    ].filter(Boolean);
    return parts.join(' | ') || 'Model review recorded.';
  }

  llmJudgeDetail(result: RequirementDraftResult): string {
    const judge = result.scorecard.llmJudge;
    if (!judge) {
      return 'The deterministic rubric still produced the score above.';
    }
    if (judge.status === 'failed') {
      return judge.warning || 'The model judge failed, but the deterministic scorecard is still available.';
    }
    return judge.summary || judge.recommendations[0] || 'The model judge completed without extra notes.';
  }

  runStatusLabel(result: RequirementDraftResult): string {
    return result.requirementCase.jiraReadinessStatus || result.run.status;
  }

  readinessDetail(result: RequirementDraftResult): string {
    const openQuestions = this.openQuestionCount(result);
    if (result.requirementCase.jiraReady) {
      return 'All gates passed for human Jira approval.';
    }
    return `${openQuestions} role question${openQuestions === 1 ? '' : 's'} still block Jira readiness.`;
  }

  isQuestionSaving(questionId: string): boolean {
    return this.activeQuestionId() === questionId;
  }

  evalStatusClass(result: RequirementDraftResult): string {
    if (this.openQuestionCount(result) > 0) {
      return 'status-warning';
    }
    return result.scorecard.passStatus === 'pass'
      ? 'status-success'
      : result.scorecard.passStatus === 'warning'
        ? 'status-warning'
        : 'status-error';
  }

  evalReason(result: RequirementDraftResult): string {
    const openQuestions = this.openQuestionCount(result);
    if (openQuestions > 0) {
      return `${openQuestions} open questions remain before Jira handoff.`;
    }
    if (result.scorecard.missingCriticalItems.length) {
      return `${result.scorecard.missingCriticalItems.length} critical eval items remain.`;
    }
    return 'Source coverage and impact mapping passed the local eval gate.';
  }

  coverageText(result: RequirementDraftResult): string {
    const entries = Object.values(result.scorecard.sourceCoverage);
    const covered = entries.filter(Boolean).length;
    return `${covered}/${entries.length}`;
  }

  private durationLabel(durationMs: number): string {
    if (durationMs < 1000) {
      return `${durationMs} ms`;
    }
    return `${(durationMs / 1000).toFixed(1)} s`;
  }

  private acceptDraftResult(result: RequirementDraftResult): void {
    const initialAnswers = Object.fromEntries(
      result.requirementCase.questions
        .filter((question) => question.answer)
        .map((question) => [question.questionId, question.answer || '']),
    );
    const initialWaivers = Object.fromEntries(
      result.requirementCase.questions
        .filter((question) => question.status === 'waived')
        .map((question) => [
          question.questionId,
          {
            reason: question.waivedReason || this.waiverReasons[0],
            note: '',
          },
        ]),
    );
    this.result.set(result);
    this.questionAnswers.set(initialAnswers);
    this.questionWaivers.set(initialWaivers);
    this.impactDetailsOpen.set(false);
  }

  private withUpdatedQuestion(
    current: RequirementDraftResult,
    questionId: string,
    updatedQuestion: ClarificationQuestion,
  ): RequirementDraftResult {
    const updatedAt = updatedQuestion.answeredAt || updatedQuestion.waivedAt || new Date().toISOString();
    const requirementCase = {
      ...current.requirementCase,
      status: 'questions_answered' as const,
      updatedAt,
      questions: current.requirementCase.questions.map((question) =>
        question.questionId === questionId ? updatedQuestion : question,
      ),
    };
    return { ...current, requirementCase };
  }

  private requirementInput(): RequirementDraftInput {
    const { teamId, app, component, roughBusinessRequest, topK, role } = this.form.getRawValue();
    return { teamId, app, component, roughBusinessRequest, topK, role };
  }

  private errorMessage(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse) {
      const detail =
        typeof error.error === 'object' && error.error && 'detail' in error.error
          ? String(error.error.detail)
          : error.message;
      return detail || fallback;
    }
    if (error instanceof Error) {
      return error.message;
    }
    return fallback;
  }

  private loadIntakeDocuments(): void {
    this.api
      .listIntakeDocuments()
      .pipe(catchError(() => of([])))
      .subscribe((documents) => this.intakeDocuments.set(documents));
  }

  private startLifecycleProgress(): void {
    this.lifecycleState.set('running');
    this.lifecycleStepIndex.set(-1);
    this.lifecycleDurations.set({});
  }

  private applyLifecycleProgress(progress: RequirementDraftLifecycleProgress): void {
    const displayStepId = this.lifecycleDisplayStepId(progress.stepId);
    const index = this.lifecycleSteps.findIndex((step) => step.id === displayStepId);
    if (index < 0) {
      return;
    }
    this.lifecycleState.set('running');
    this.lifecycleStepIndex.set(index);
    if (progress.state === 'complete' && progress.durationMs !== undefined) {
      this.lifecycleDurations.update((durations) => ({
        ...durations,
        [displayStepId]: (durations[displayStepId] ?? 0) + (progress.durationMs ?? 0),
      }));
    }
  }

  private lifecycleDisplayStepId(stepId: RequirementDraftLifecycleProgress['stepId']): string {
    if (['create_case', 'analyze_evidence'].includes(stepId)) {
      return 'create_analyze_phase';
    }
    if (['prepare_jira_context', 'draft_jira', 'readiness_check'].includes(stepId)) {
      return 'draft_jira_phase';
    }
    if (['eval_score', 'llm_judge', 'load_result'].includes(stepId)) {
      return 'eval_phase';
    }
    return stepId;
  }

  private completeLifecycleProgress(): void {
    this.lifecycleStepIndex.set(this.lifecycleSteps.length - 1);
    this.lifecycleState.set('complete');
  }

  private failLifecycleProgress(): void {
    this.lifecycleStepIndex.update((current) => Math.max(current, 0));
    this.lifecycleState.set('error');
  }

  private looksLikeCodeFileReference(source: string): boolean {
    return /\.(java|ts|tsx|js|jsx|py|go|rb|cs|kt|scala)$/i.test(source);
  }

  private isAffectedFileReference(areaType: string, source: string): boolean {
    if (!this.looksLikeCodeFileReference(source) || areaType === 'workflow') {
      return false;
    }
    if (areaType === 'test' && !/test/i.test(source)) {
      return false;
    }
    return true;
  }
}
