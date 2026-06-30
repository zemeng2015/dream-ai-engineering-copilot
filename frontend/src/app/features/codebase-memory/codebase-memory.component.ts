// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { CodebaseFile } from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-codebase-memory',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './codebase-memory.component.html',
})
export class CodebaseMemoryComponent {
  private readonly dream = inject(MockDreamService);
  private readonly fb = inject(FormBuilder);

  readonly files = this.dream.listCodebaseFiles();
  readonly results = signal<CodebaseFile[]>(this.dream.searchCodebase({ query: 'status tracker batch task', topK: 8 }));
  readonly selectedFile = signal<CodebaseFile | null>(this.results()[0] ?? null);

  readonly form = this.fb.nonNullable.group({
    query: 'status tracker batch task',
    topK: 8,
  });

  readonly conceptList = computed(() =>
    Array.from(new Set(this.files.flatMap((file) => file.concepts)))
      .sort()
      .slice(0, 18),
  );

  search(): void {
    const value = this.form.getRawValue();
    const matches = this.dream.searchCodebase({
      query: value.query,
      topK: value.topK,
    });
    this.results.set(matches);
    this.selectedFile.set(matches[0] ?? null);
  }
}
