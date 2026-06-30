// SPDX-License-Identifier: Apache-2.0

import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MockDreamService } from '../../core/mock-dream.service';
import { PrReviewComponent } from '../pr-review/pr-review.component';
import { RequirementDraftComponent } from '../requirement-draft/requirement-draft.component';

type WorkbenchMode = 'requirement' | 'pr';

interface WorkbenchModeItem {
  id: WorkbenchMode;
  label: string;
  summary: string;
}

@Component({
  selector: 'app-engineering-workbench',
  standalone: true,
  imports: [PrReviewComponent, RequirementDraftComponent, RouterLink],
  templateUrl: './engineering-workbench.component.html',
  styleUrl: './engineering-workbench.component.scss',
})
export class EngineeringWorkbenchComponent {
  private readonly dream = inject(MockDreamService);

  readonly activeMode = signal<WorkbenchMode>('requirement');
  readonly context = this.dream.getContextIntelligenceSnapshot();
  readonly primaryCase = this.dream.requirementCases()[0];
  readonly detectedConcepts = [
    'execution status',
    'task progress',
    'stale polling',
    'operator escalation',
    'status transition tests',
  ];

  readonly modes: WorkbenchModeItem[] = [
    {
      id: 'requirement',
      label: 'Requirement Case',
      summary: 'Rough business request -> impact map -> open questions -> Jira-ready draft.',
    },
    {
      id: 'pr',
      label: 'PR Review',
      summary: 'Diff and Jira context -> related code -> evidence-backed review aid.',
    },
  ];

  selectMode(mode: WorkbenchMode): void {
    this.activeMode.set(mode);
  }
}
