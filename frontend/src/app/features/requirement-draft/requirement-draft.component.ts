// SPDX-License-Identifier: Apache-2.0

import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { RequirementDraftInput, RequirementDraftResult } from '../../core/dream-models';
import { DreamApiService } from '../../core/dream-api.service';
import { UiIconComponent } from '../../shared/ui-icon.component';

interface AffectedFileView {
  path: string;
  areaType: string;
  reason: string;
}

@Component({
  selector: 'app-requirement-draft',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, UiIconComponent],
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
  readonly activeQuestionId = signal<string | null>(null);
  readonly advancedOpen = signal(false);
  readonly impactDetailsOpen = signal(false);

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

  generate(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const input = this.requirementInput();
    this.apiError.set(null);
    this.isLoading.set(true);
    this.api.draftRequirementWithOpenAI(input).subscribe({
      next: (result) => {
        this.acceptDraftResult(result);
        this.isLoading.set(false);
      },
      error: (error: unknown) => {
        this.apiError.set(this.errorMessage(error, 'OpenAI requirement case request failed.'));
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

  updateQuestionAnswer(questionId: string, event: Event): void {
    const value = event.target instanceof HTMLTextAreaElement ? event.target.value : '';
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
        const requirementCase = {
          ...current.requirementCase,
          status: 'questions_answered' as const,
          updatedAt: updatedQuestion.answeredAt || new Date().toISOString(),
          questions: current.requirementCase.questions.map((question) =>
            question.questionId === questionId ? updatedQuestion : question,
          ),
        };
        this.result.set({ ...current, requirementCase });
        this.activeQuestionId.set(null);
      },
      error: (error: unknown) => {
        this.apiError.set(this.errorMessage(error, 'Failed to save answer to the API.'));
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
    this.api
      .regenerateRequirementCaseWithOpenAI(this.requirementInput(), current.requirementCase.caseId)
      .subscribe({
        next: (result) => {
          this.acceptDraftResult(result);
          this.isLoading.set(false);
        },
        error: (error: unknown) => {
          this.apiError.set(this.errorMessage(error, 'Failed to regenerate Jira draft.'));
          this.isLoading.set(false);
        },
    });
  }

  readinessLabel(result: RequirementDraftResult): string {
    return result.requirementCase.jiraReady ? 'Jira ready' : 'Needs answers';
  }

  openQuestionCount(result: RequirementDraftResult): number {
    return result.requirementCase.questions.filter((question) => question.status !== 'answered').length;
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

  private acceptDraftResult(result: RequirementDraftResult): void {
    const initialAnswers = Object.fromEntries(
      result.requirementCase.questions
        .filter((question) => question.answer)
        .map((question) => [question.questionId, question.answer || '']),
    );
    this.result.set(result);
    this.questionAnswers.set(initialAnswers);
    this.impactDetailsOpen.set(false);
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

  private looksLikeFileReference(source: string): boolean {
    return /\.[a-z0-9]+$/i.test(source);
  }

  private isAffectedFileReference(areaType: string, source: string): boolean {
    if (!this.looksLikeFileReference(source) || areaType === 'workflow') {
      return false;
    }
    if (areaType === 'test' && !/test/i.test(source)) {
      return false;
    }
    return true;
  }
}
