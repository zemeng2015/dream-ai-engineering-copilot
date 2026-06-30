// SPDX-License-Identifier: Apache-2.0

import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { KnowledgeChunk } from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-knowledge-base',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './knowledge-base.component.html',
})
export class KnowledgeBaseComponent {
  private readonly dream = inject(MockDreamService);
  private readonly fb = inject(FormBuilder);

  readonly apps = this.dream.listApps();
  readonly docTypes = this.dream.listDocTypes();
  readonly chunks = signal<KnowledgeChunk[]>(this.dream.searchKnowledge({ query: 'execution status stuck running', topK: 8 }));
  readonly selectedChunk = signal<KnowledgeChunk | null>(this.chunks()[0] ?? null);

  readonly form = this.fb.nonNullable.group({
    query: 'execution status stuck running',
    app: '',
    component: '',
    docType: '',
    topK: 8,
  });

  search(): void {
    const value = this.form.getRawValue();
    const results = this.dream.searchKnowledge({
      query: value.query,
      app: value.app || undefined,
      component: value.component || undefined,
      docType: value.docType || undefined,
      topK: value.topK,
    });
    this.chunks.set(results);
    this.selectedChunk.set(results[0] ?? null);
  }
}
