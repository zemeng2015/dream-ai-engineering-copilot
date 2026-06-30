// SPDX-License-Identifier: Apache-2.0

import { Component, signal } from '@angular/core';

import { CodebaseMemoryComponent } from '../codebase-memory/codebase-memory.component';
import { EvidenceGraphComponent } from '../evidence-graph/evidence-graph.component';
import { KnowledgeBaseComponent } from '../knowledge-base/knowledge-base.component';
import { KnowledgeIntakeComponent } from '../knowledge-intake/knowledge-intake.component';

type MemoryHubTab = 'sources' | 'packs' | 'codebase' | 'graph';

interface MemoryHubNavItem {
  id: MemoryHubTab;
  label: string;
}

@Component({
  selector: 'app-memory-hub',
  standalone: true,
  imports: [
    CodebaseMemoryComponent,
    EvidenceGraphComponent,
    KnowledgeBaseComponent,
    KnowledgeIntakeComponent,
  ],
  templateUrl: './memory-hub.component.html',
  styleUrl: './memory-hub.component.scss',
})
export class MemoryHubComponent {
  readonly activeTab = signal<MemoryHubTab>('sources');

  readonly tabs: MemoryHubNavItem[] = [
    {
      id: 'sources',
      label: 'Sources',
    },
    {
      id: 'packs',
      label: 'Knowledge Packs',
    },
    {
      id: 'codebase',
      label: 'Code Index',
    },
    {
      id: 'graph',
      label: 'Retrieval Paths',
    },
  ];

  selectTab(tab: MemoryHubTab): void {
    this.activeTab.set(tab);
  }
}
