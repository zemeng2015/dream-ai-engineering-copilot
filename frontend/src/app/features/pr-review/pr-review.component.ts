// SPDX-License-Identifier: Apache-2.0

import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { PrReviewResult } from '../../core/dream-models';
import { DreamApiService } from '../../core/dream-api.service';
import { UiIconComponent } from '../../shared/ui-icon.component';

@Component({
  selector: 'app-pr-review',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, UiIconComponent],
  templateUrl: './pr-review.component.html',
  styleUrl: './pr-review.component.scss',
})
export class PrReviewComponent {
  private readonly api = inject(DreamApiService);
  private readonly fb = inject(FormBuilder);

  readonly apps = ['ForecastDemo', 'BatchJobDemo', 'OutputPreviewDemo'];
  readonly result = signal<PrReviewResult | null>(null);
  readonly isLoading = signal(false);
  readonly apiError = signal<string | null>(null);
  readonly advancedOpen = signal(false);
  readonly codeDetailsOpen = signal(false);

  readonly form = this.fb.nonNullable.group({
    executionMode: ['openai', Validators.required],
    teamId: ['demo_team', Validators.required],
    app: ['OutputPreviewDemo', Validators.required],
    component: ['output-collection', Validators.required],
    diffText: [MOCK_DIFF_TEXT, Validators.required],
    jiraContext: [MOCK_JIRA_CONTEXT, Validators.required],
    topK: [5, [Validators.required, Validators.min(1), Validators.max(20)]],
  });

  generate(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const input = {
      teamId: raw.teamId,
      app: raw.app,
      component: raw.component,
      diffText: raw.diffText,
      jiraContext: raw.jiraContext,
      topK: raw.topK,
    };
    this.apiError.set(null);
    this.isLoading.set(true);
    this.api.reviewPrWithOpenAI(input).subscribe({
      next: (result) => {
        this.acceptReviewResult(result);
        this.isLoading.set(false);
      },
      error: (error: unknown) => {
        this.apiError.set(error instanceof Error ? error.message : 'OpenAI API request failed.');
        this.isLoading.set(false);
      },
    });
  }

  toggleAdvancedSettings(): void {
    this.advancedOpen.update((open) => !open);
  }

  toggleCodeDetails(): void {
    this.codeDetailsOpen.update((open) => !open);
  }

  riskStatusClass(review: PrReviewResult): string {
    if (review.risk === 'High') {
      return 'status-error';
    }
    return review.risk === 'Medium' ? 'status-warning' : 'status-success';
  }

  evalDecision(review: PrReviewResult): string {
    if (review.risk === 'High') {
      return 'Needs senior review';
    }
    return review.scorecard.passStatus === 'pass' ? 'Ready for human review' : 'Needs review';
  }

  evalStatusClass(review: PrReviewResult): string {
    if (review.risk === 'High') {
      return 'status-error';
    }
    return review.scorecard.passStatus === 'pass'
      ? 'status-success'
      : review.scorecard.passStatus === 'warning'
        ? 'status-warning'
        : 'status-error';
  }

  evalReason(review: PrReviewResult): string {
    if (!review.relatedCode.length) {
      return 'No related codebase memory was matched; reviewer should inspect manually.';
    }
    if (review.risk === 'High') {
      return 'Large or broad diff requires senior reviewer confirmation.';
    }
    return 'Related code, memory docs, and test context were found for reviewer handoff.';
  }

  coverageText(review: PrReviewResult): string {
    const entries = Object.values(review.scorecard.sourceCoverage);
    const covered = entries.filter(Boolean).length;
    return `${covered}/${entries.length}`;
  }

  sourceFamilies(review: PrReviewResult): Array<{ label: string; count: number }> {
    const counts = new Map<string, number>();
    for (const source of review.sourcesUsed) {
      const label = this.sourceTypeLabel(source.sourceType);
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    return Array.from(counts, ([label, count]) => ({ label, count }));
  }

  codeLayers(review: PrReviewResult): string {
    return Array.from(new Set(review.relatedCode.map((file) => file.layer))).join(', ') || 'No code memory';
  }

  changedFileName(path: string): string {
    return path.split('/').pop() || path;
  }

  sourceTypeLabel(sourceType: string): string {
    return sourceType
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private acceptReviewResult(result: PrReviewResult): void {
    this.result.set(result);
    this.codeDetailsOpen.set(false);
  }
}

const MOCK_DIFF_TEXT = `diff --git a/backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java b/backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java
+ public OutputArtifact collect(String executionId, String taskId, StorageObject object) {
+   String key = executionId + ":" + taskId + ":" + object.name();
+   if (artifactRepository.existsByIdempotencyKey(key)) {
+     return artifactRepository.findByIdempotencyKey(key);
+   }
+   return artifactRepository.save(OutputArtifact.from(object, key));
+ }
diff --git a/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java b/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java
+ @Test
+ void doesNotDuplicateArtifactsAfterStorageRetry() {
+   collector.collect("exec-1", "task-1", object);
+   collector.collect("exec-1", "task-1", object);
+   assertThat(repository.count()).isEqualTo(1);
+ }`;

const MOCK_JIRA_CONTEXT = `DFP-110 Make output collection idempotent.
OutputCollector should prevent duplicate output artifacts when storage retry returns the same file more than once.`;
