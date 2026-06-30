// SPDX-License-Identifier: Apache-2.0

import { Component, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { RequirementDraftResult } from '../../core/dream-models';
import { DreamApiService } from '../../core/dream-api.service';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-requirement-draft',
  standalone: true,
  imports: [DecimalPipe, ReactiveFormsModule],
  templateUrl: './requirement-draft.component.html',
})
export class RequirementDraftComponent {
  private readonly dream = inject(MockDreamService);
  private readonly api = inject(DreamApiService);
  private readonly fb = inject(FormBuilder);

  readonly apps = this.dream.listApps();
  readonly result = signal<RequirementDraftResult | null>(null);
  readonly isLoading = signal(false);
  readonly apiError = signal<string | null>(null);
  readonly questionAnswers = signal<Record<string, string>>({});

  readonly form = this.fb.nonNullable.group({
    executionMode: ['mock', Validators.required],
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
    const { executionMode, ...input } = this.form.getRawValue();
    this.apiError.set(null);
    if (executionMode === 'openai') {
      this.isLoading.set(true);
      this.api.draftRequirementWithOpenAI(input).subscribe({
        next: (result) => {
          this.result.set(result);
          this.isLoading.set(false);
        },
        error: (error: unknown) => {
          this.apiError.set(error instanceof Error ? error.message : 'OpenAI API request failed.');
          this.isLoading.set(false);
        },
      });
      return;
    }
    this.result.set(this.dream.draftRequirement(input));
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
    const now = new Date().toISOString();
    const requirementCase = {
      ...current.requirementCase,
      status: 'questions_answered' as const,
      updatedAt: now,
      questions: current.requirementCase.questions.map((question) =>
        question.questionId === questionId
          ? {
              ...question,
              status: 'answered' as const,
              answer,
              answeredBy: 'Demo Reviewer',
              answeredAt: now,
            }
          : question,
      ),
    };
    this.result.set({ ...current, requirementCase });
  }

  regenerateJiraDraft(): void {
    const current = this.result();
    if (!current) {
      return;
    }
    const allAnswered = current.requirementCase.questions.every(
      (question) => question.status === 'answered',
    );
    const requirementCase = {
      ...current.requirementCase,
      status: allAnswered ? ('jira_ready_draft' as const) : ('jira_draft_needs_answers' as const),
      jiraReady: allAnswered,
      jiraReadinessStatus: allAnswered
        ? ('jira_ready_draft' as const)
        : ('jira_draft_needs_answers' as const),
      updatedAt: new Date().toISOString(),
    };
    const markdown = buildJiraDraftWithAnswers(requirementCase);
    this.result.set({
      ...current,
      markdown,
      requirementCase: {
        ...requirementCase,
        jiraDraft: markdown,
      },
      warnings: allAnswered
        ? ['Jira-ready draft is ready for final human approval.']
        : ['Open questions remain before this can be treated as Jira-ready.'],
    });
  }

  readinessLabel(result: RequirementDraftResult): string {
    return result.requirementCase.jiraReady ? 'Jira ready' : 'Needs answers';
  }
}

function buildJiraDraftWithAnswers(requirementCase: RequirementDraftResult['requirementCase']): string {
  const questionLines = requirementCase.questions
    .map(
      (question) =>
        `- [${question.targetRole}] ${question.question} Status: ${question.status}. ` +
        `Answer: ${question.answer || 'pending human response'}`,
    )
    .join('\n');
  return `${requirementCase.jiraDraft}

## Human Answers Captured
${questionLines}

## Jira Readiness
${requirementCase.jiraReady ? 'Ready after all open questions were answered.' : 'Not ready; open questions remain.'}
`;
}
