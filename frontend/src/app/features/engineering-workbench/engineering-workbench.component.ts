// SPDX-License-Identifier: Apache-2.0

import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

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
  private readonly route = inject(ActivatedRoute);
  readonly activeMode = signal<WorkbenchMode>('requirement');

  readonly modes: WorkbenchModeItem[] = [
    {
      id: 'requirement',
      label: 'Jira Draft',
      summary: 'Business request -> memory and impact -> open questions -> Jira proposal.',
    },
    {
      id: 'pr',
      label: 'PR Review',
      summary: 'Diff and Jira context -> related code -> evidence-backed review aid.',
    },
  ];

  constructor() {
    this.route.data.subscribe((data) => {
      const mode = data['mode'];
      if (this.isWorkbenchMode(mode)) {
        this.activeMode.set(mode);
      }
    });
  }

  selectMode(mode: WorkbenchMode): void {
    this.activeMode.set(mode);
  }

  private isWorkbenchMode(value: unknown): value is WorkbenchMode {
    return value === 'requirement' || value === 'pr';
  }
}
