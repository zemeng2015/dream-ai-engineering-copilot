// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { CodebaseFile } from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';
import { UiIconComponent } from '../../shared/ui-icon.component';

interface CodeMapNode {
  id: string;
  file: CodebaseFile;
  title: string;
  lane: string;
  x: number;
  y: number;
  matched: boolean;
  selected: boolean;
}

interface CodeMapEdge {
  id: string;
  from: CodeMapNode;
  to: CodeMapNode;
  label: string;
  relation: 'api' | 'calls' | 'config' | 'tests';
  active: boolean;
}

@Component({
  selector: 'app-codebase-memory',
  standalone: true,
  imports: [ReactiveFormsModule, UiIconComponent],
  templateUrl: './codebase-memory.component.html',
  styleUrl: './codebase-memory.component.scss',
})
export class CodebaseMemoryComponent {
  private readonly dream = inject(MockDreamService);
  private readonly fb = inject(FormBuilder);

  readonly files = this.dream.listCodebaseFiles();
  readonly results = signal<CodebaseFile[]>(this.dream.searchCodebase({ query: 'status tracker batch task', topK: 8 }));
  readonly selectedFile = signal<CodebaseFile | null>(this.results()[0] ?? null);
  readonly searchCollapsed = signal(true);
  readonly activeSearch = signal({
    query: 'status tracker batch task',
    topK: 8,
  });

  readonly form = this.fb.nonNullable.group({
    query: 'status tracker batch task',
    topK: 8,
  });

  readonly searchSummary = computed(() => {
    const value = this.activeSearch();
    return value.query.trim() ? `Query: ${value.query.trim()}` : 'All indexed files';
  });

  readonly codeMapNodes = computed<CodeMapNode[]>(() => {
    const matchedIds = new Set(this.results().map((file) => file.id));
    const selectedId = this.selectedFile()?.id;
    return this.files.map((file) => {
      const position = CODE_MAP_POSITIONS[file.id] ?? { x: 50, y: 50 };
      return {
        id: file.id,
        file,
        title: file.path.split('/').pop() ?? file.path,
        lane: nodeLane(file),
        x: position.x,
        y: position.y,
        matched: matchedIds.has(file.id),
        selected: selectedId === file.id,
      };
    });
  });

  readonly codeMapEdges = computed<CodeMapEdge[]>(() => {
    const nodesById = new Map(this.codeMapNodes().map((node) => [node.id, node]));
    const selectedId = this.selectedFile()?.id;
    return CODE_MAP_EDGES.flatMap((edge) => {
      const from = nodesById.get(edge.from);
      const to = nodesById.get(edge.to);
      if (!from || !to) {
        return [];
      }
      return [
        {
          ...edge,
          from,
          to,
          active: selectedId ? from.id === selectedId || to.id === selectedId : from.matched && to.matched,
        },
      ];
    });
  });

  readonly selectedConnections = computed(() => {
    const selected = this.selectedFile();
    if (!selected) {
      return [];
    }
    return this.codeMapEdges()
      .filter((edge) => edge.from.id === selected.id || edge.to.id === selected.id)
      .map((edge) =>
        edge.from.id === selected.id
          ? `${edge.label}: ${edge.to.title}`
          : `${edge.from.title}: ${edge.label}`,
      );
  });

  toggleSearch(): void {
    this.searchCollapsed.update((collapsed) => !collapsed);
  }

  selectFile(file: CodebaseFile): void {
    this.selectedFile.set(file);
  }

  search(): void {
    const value = this.form.getRawValue();
    const matches = this.dream.searchCodebase({
      query: value.query,
      topK: value.topK,
    });
    this.results.set(matches);
    this.selectedFile.set(matches[0] ?? null);
    this.activeSearch.set(value);
    this.searchCollapsed.set(true);
  }
}

const CODE_MAP_POSITIONS: Record<string, { x: number; y: number }> = {
  'code-execution-monitor': { x: 16, y: 28 },
  'code-job-api': { x: 16, y: 62 },
  'code-execution-controller': { x: 38, y: 25 },
  'code-execution-service': { x: 38, y: 52 },
  'code-status-tracker': { x: 38, y: 78 },
  'code-state-machine': { x: 64, y: 18 },
  'code-batch-adapter': { x: 64, y: 42 },
  'code-input-validator': { x: 64, y: 66 },
  'code-output-collector': { x: 64, y: 86 },
  'code-output-preview': { x: 64, y: 28 },
  'test-status-tracker': { x: 84, y: 72 },
  'test-output-collector': { x: 84, y: 88 },
};

const CODE_MAP_EDGES: Array<{
  id: string;
  from: string;
  to: string;
  label: string;
  relation: CodeMapEdge['relation'];
}> = [
  { id: 'edge-monitor-api', from: 'code-execution-monitor', to: 'code-job-api', label: 'uses', relation: 'api' },
  { id: 'edge-api-controller', from: 'code-job-api', to: 'code-execution-controller', label: 'calls', relation: 'api' },
  {
    id: 'edge-controller-service',
    from: 'code-execution-controller',
    to: 'code-execution-service',
    label: 'delegates',
    relation: 'calls',
  },
  {
    id: 'edge-service-tracker',
    from: 'code-execution-service',
    to: 'code-status-tracker',
    label: 'updates',
    relation: 'calls',
  },
  {
    id: 'edge-service-batch',
    from: 'code-execution-service',
    to: 'code-batch-adapter',
    label: 'runs',
    relation: 'calls',
  },
  {
    id: 'edge-service-output',
    from: 'code-execution-service',
    to: 'code-output-collector',
    label: 'collects',
    relation: 'calls',
  },
  {
    id: 'edge-state-service',
    from: 'code-state-machine',
    to: 'code-execution-service',
    label: 'orchestrates',
    relation: 'config',
  },
  {
    id: 'edge-batch-validator',
    from: 'code-batch-adapter',
    to: 'code-input-validator',
    label: 'processor',
    relation: 'calls',
  },
  {
    id: 'edge-job-preview',
    from: 'code-job-api',
    to: 'code-output-preview',
    label: 'preview',
    relation: 'api',
  },
  {
    id: 'edge-tracker-test',
    from: 'code-status-tracker',
    to: 'test-status-tracker',
    label: 'tested by',
    relation: 'tests',
  },
  {
    id: 'edge-output-test',
    from: 'code-output-collector',
    to: 'test-output-collector',
    label: 'tested by',
    relation: 'tests',
  },
];

function nodeLane(file: CodebaseFile): string {
  if (file.role === 'test') {
    return 'test';
  }
  if (file.role === 'config') {
    return 'workflow';
  }
  if (file.language === 'typescript') {
    return 'ui';
  }
  if (file.language === 'python') {
    return 'processor';
  }
  return 'service';
}
