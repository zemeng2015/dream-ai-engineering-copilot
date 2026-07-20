// SPDX-License-Identifier: Apache-2.0

import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';

import { DreamApiService } from '../../core/dream-api.service';
import { EngineeringLoopResult, EngineeringLoopStageName } from '../../core/dream-models';

@Component({
  selector: 'app-engineering-loop',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './engineering-loop.component.html',
  styleUrl: './engineering-loop.component.scss',
})
export class EngineeringLoopComponent {
  private readonly api = inject(DreamApiService);
  private readonly fb = inject(FormBuilder);

  readonly running = signal(false);
  readonly result = signal<EngineeringLoopResult | null>(null);
  readonly error = signal('');
  readonly stageOrder: EngineeringLoopStageName[] = [
    'memory',
    'jira',
    'pr_review',
    'testgen',
    'eval',
  ];

  readonly form = this.fb.nonNullable.group({
    rawRequest: [
      'Add governed async job status visibility. Preserve existing behavior, expose terminal '
        + 'states, require source-backed Jira acceptance criteria, review the PR against team '
        + 'memory, generate focused JUnit 5 candidates, and evaluate every artifact before handoff.',
      [Validators.required, Validators.minLength(40)],
    ],
    liveGpt56: true,
  });

  run(): void {
    if (this.form.invalid || this.running()) {
      this.form.markAllAsTouched();
      return;
    }
    this.error.set('');
    this.result.set(null);
    this.running.set(true);
    this.api
      .runEngineeringLoop(this.form.getRawValue())
      .pipe(finalize(() => this.running.set(false)))
      .subscribe({
        next: (result) => this.result.set(result),
        error: (error: { error?: { detail?: string }; message?: string }) =>
          this.error.set(
            error.error?.detail
              || error.message
              || 'The engineering loop could not complete.',
          ),
      });
  }

  stageLabel(stage: EngineeringLoopStageName): string {
    const labels: Record<EngineeringLoopStageName, string> = {
      memory: 'Govern memory',
      jira: 'Draft Jira',
      pr_review: 'Review PR',
      testgen: 'Generate tests',
      eval: 'Evaluate loop',
    };
    return labels[stage];
  }
}
