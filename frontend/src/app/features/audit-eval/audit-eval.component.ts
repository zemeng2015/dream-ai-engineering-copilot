// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { KeyValuePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { AuditRun } from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-audit-eval',
  standalone: true,
  imports: [KeyValuePipe, ReactiveFormsModule],
  templateUrl: './audit-eval.component.html',
})
export class AuditEvalComponent {
  private readonly dream = inject(MockDreamService);
  private readonly fb = inject(FormBuilder);

  readonly runs = this.dream.auditRuns;
  readonly ratings = this.dream.ratings;
  readonly scorecards = this.dream.scorecards;
  readonly selectedRun = signal<AuditRun | null>(this.runs()[0] ?? null);
  readonly selectedRatings = computed(() =>
    this.ratings().filter((rating) => rating.runId === this.selectedRun()?.runId),
  );

  readonly ratingForm = this.fb.nonNullable.group({
    usefulnessScore: [4, [Validators.required, Validators.min(1), Validators.max(5)]],
    correctnessScore: [4, [Validators.required, Validators.min(1), Validators.max(5)]],
    comments: ['Useful mock output; needs human review before real use.', Validators.required],
  });

  selectRun(run: AuditRun): void {
    this.selectedRun.set(run);
  }

  submitRating(): void {
    const run = this.selectedRun();
    if (!run || this.ratingForm.invalid) {
      this.ratingForm.markAllAsTouched();
      return;
    }
    this.dream.addRating({
      runId: run.runId,
      ...this.ratingForm.getRawValue(),
    });
  }
}
