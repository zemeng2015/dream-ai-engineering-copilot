// SPDX-License-Identifier: Apache-2.0

import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { PrReviewResult } from '../../core/dream-models';
import { DreamApiService } from '../../core/dream-api.service';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-pr-review',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './pr-review.component.html',
})
export class PrReviewComponent {
  private readonly dream = inject(MockDreamService);
  private readonly api = inject(DreamApiService);
  private readonly fb = inject(FormBuilder);

  readonly apps = this.dream.listApps();
  readonly result = signal<PrReviewResult | null>(null);
  readonly isLoading = signal(false);
  readonly apiError = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    executionMode: ['mock', Validators.required],
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
    const { executionMode, ...input } = this.form.getRawValue();
    this.apiError.set(null);
    if (executionMode === 'openai') {
      this.isLoading.set(true);
      this.api.reviewPrWithOpenAI(input).subscribe({
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
    this.result.set(this.dream.reviewPr(input));
  }
}

const MOCK_DIFF_TEXT = `diff --git a/examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java b/examples/dfp-demo-repo/backend-api/src/main/java/com/democorp/dfp/output/OutputCollector.java
+ public OutputArtifact collect(String executionId, String taskId, StorageObject object) {
+   String key = executionId + ":" + taskId + ":" + object.name();
+   if (artifactRepository.existsByIdempotencyKey(key)) {
+     return artifactRepository.findByIdempotencyKey(key);
+   }
+   return artifactRepository.save(OutputArtifact.from(object, key));
+ }
diff --git a/examples/dfp-demo-repo/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java b/examples/dfp-demo-repo/backend-api/src/test/java/com/democorp/dfp/output/OutputCollectorTest.java
+ @Test
+ void doesNotDuplicateArtifactsAfterStorageRetry() {
+   collector.collect("exec-1", "task-1", object);
+   collector.collect("exec-1", "task-1", object);
+   assertThat(repository.count()).isEqualTo(1);
+ }`;

const MOCK_JIRA_CONTEXT = `DFP-110 Make output collection idempotent.
OutputCollector should prevent duplicate output artifacts when storage retry returns the same file more than once.`;
