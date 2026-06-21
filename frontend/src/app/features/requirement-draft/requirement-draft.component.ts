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
}
