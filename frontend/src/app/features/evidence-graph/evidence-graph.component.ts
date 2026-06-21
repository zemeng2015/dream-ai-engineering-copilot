import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { EvidenceGraphPath } from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-evidence-graph',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './evidence-graph.component.html',
})
export class EvidenceGraphComponent {
  private readonly dream = inject(MockDreamService);
  private readonly fb = inject(FormBuilder);

  readonly nodes = this.dream.listEvidenceGraphNodes();
  readonly results = signal<EvidenceGraphPath[]>(
    this.dream.searchEvidenceGraph({ query: 'execution status', topK: 8 }),
  );
  readonly selectedPath = signal<EvidenceGraphPath | null>(this.results()[0] ?? null);

  readonly form = this.fb.nonNullable.group({
    query: 'execution status',
    topK: 8,
  });

  readonly nodeSummary = computed(() =>
    Array.from(new Set(this.nodes.map((node) => node.type)))
      .sort()
      .map((type) => ({
        type,
        count: this.nodes.filter((node) => node.type === type).length,
      })),
  );

  search(): void {
    const value = this.form.getRawValue();
    const matches = this.dream.searchEvidenceGraph({ query: value.query, topK: value.topK });
    this.results.set(matches);
    this.selectedPath.set(matches[0] ?? null);
  }
}
