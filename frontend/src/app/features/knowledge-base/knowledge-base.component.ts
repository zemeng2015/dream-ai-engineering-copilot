// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { KnowledgeChunk } from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';
import { UiIconComponent } from '../../shared/ui-icon.component';

interface KnowledgeSourceGroup {
  sourceType: KnowledgeChunk['sourceType'];
  label: string;
  chunks: KnowledgeChunk[];
}

@Component({
  selector: 'app-knowledge-base',
  standalone: true,
  imports: [ReactiveFormsModule, UiIconComponent],
  templateUrl: './knowledge-base.component.html',
  styleUrl: './knowledge-base.component.scss',
})
export class KnowledgeBaseComponent {
  private readonly dream = inject(MockDreamService);
  private readonly fb = inject(FormBuilder);

  readonly apps = this.dream.listApps();
  readonly docTypes = this.dream.listDocTypes();
  readonly chunks = signal<KnowledgeChunk[]>(this.dream.searchKnowledge({ query: 'execution status stuck running', topK: 8 }));
  readonly selectedChunk = signal<KnowledgeChunk | null>(this.chunks()[0] ?? null);
  readonly searchCollapsed = signal(true);
  readonly activeSearch = signal({
    query: 'execution status stuck running',
    app: '',
    component: '',
    docType: '',
    topK: 8,
  });
  readonly sourceGroups = computed<KnowledgeSourceGroup[]>(() => {
    const grouped = new Map<KnowledgeChunk['sourceType'], KnowledgeChunk[]>();
    for (const chunk of this.chunks()) {
      grouped.set(chunk.sourceType, [...(grouped.get(chunk.sourceType) ?? []), chunk]);
    }
    return Array.from(grouped.entries()).map(([sourceType, chunks]) => ({
      sourceType,
      label: this.sourceTypeLabel(sourceType),
      chunks,
    }));
  });
  readonly searchSummary = computed(() => {
    const value = this.activeSearch();
    const summaryParts = [value.query.trim() ? `Query: ${value.query.trim()}` : 'All knowledge'];
    if (value.component.trim()) {
      summaryParts.push(`Component: ${value.component.trim()}`);
    }
    if (value.app) {
      summaryParts.push(`App: ${value.app}`);
    }
    if (value.docType) {
      summaryParts.push(`Docs: ${value.docType}`);
    }
    return summaryParts.join(' | ');
  });

  readonly form = this.fb.nonNullable.group({
    query: 'execution status stuck running',
    app: '',
    component: '',
    docType: '',
    topK: 8,
  });

  toggleSearch(): void {
    this.searchCollapsed.update((collapsed) => !collapsed);
  }

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
    this.activeSearch.set(value);
    this.searchCollapsed.set(true);
  }

  selectChunk(chunk: KnowledgeChunk): void {
    this.selectedChunk.set(chunk);
  }

  sourceHref(chunk: KnowledgeChunk): string {
    const encodedPath = chunk.sourcePath.split('/').map(encodeURIComponent).join('/');
    return `https://github.com/zemeng2015/dream-ai-engineering-copilot/blob/main/${encodedPath}`;
  }

  sourceTypeLabel(sourceType: KnowledgeChunk['sourceType']): string {
    switch (sourceType) {
      case 'architecture_doc':
        return 'Architecture';
      case 'concept_memory':
        return 'Concept Memory';
      case 'domain_doc':
        return 'Domain Docs';
      case 'graph_evidence':
        return 'Graph Evidence';
      case 'historical_jira':
        return 'Historical Jira';
      case 'historical_pr':
        return 'Historical PR';
      case 'incident':
        return 'Incidents';
      case 'runbook':
        return 'Runbooks';
      case 'testing_doc':
        return 'Testing';
      case 'code_file':
        return 'Code';
      case 'test_file':
        return 'Tests';
      default:
        return String(sourceType).replaceAll('_', ' ');
    }
  }
}
