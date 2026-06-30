// SPDX-License-Identifier: Apache-2.0

import { Component, inject, signal } from '@angular/core';

import { MockDreamService } from '../../core/mock-dream.service';
import { AuditEvalComponent } from '../audit-eval/audit-eval.component';
import { ContextIntelligenceComponent } from '../context-intelligence/context-intelligence.component';

type TrustCenterTab = 'context' | 'audit';

interface TrustCenterTabItem {
  id: TrustCenterTab;
  label: string;
  description: string;
}

@Component({
  selector: 'app-trust-center',
  standalone: true,
  imports: [AuditEvalComponent, ContextIntelligenceComponent],
  templateUrl: './trust-center.component.html',
  styleUrl: './trust-center.component.scss',
})
export class TrustCenterComponent {
  private readonly dream = inject(MockDreamService);

  readonly activeTab = signal<TrustCenterTab>('context');
  readonly context = this.dream.getContextIntelligenceSnapshot();
  readonly auditRuns = this.dream.auditRuns;
  readonly scorecards = this.dream.scorecards;

  readonly tabs: TrustCenterTabItem[] = [
    {
      id: 'context',
      label: 'Retrieval Trust',
      description: 'Inspect retrieval trail, context pack, evidence cards, prompt preview, and logic chain.',
    },
    {
      id: 'audit',
      label: 'Eval & Audit',
      description: 'Review scorecards, human ratings, run history, and deterministic quality gates.',
    },
  ];

  selectTab(tab: TrustCenterTab): void {
    this.activeTab.set(tab);
  }
}
