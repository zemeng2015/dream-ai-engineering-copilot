// SPDX-License-Identifier: Apache-2.0

import { Component } from '@angular/core';

import { UiIconComponent } from '../../shared/ui-icon.component';

interface ComparisonRow {
  dimension: string;
  stateless: string;
  dream: string;
}

@Component({
  selector: 'app-leadership-comparison',
  standalone: true,
  imports: [UiIconComponent],
  templateUrl: './leadership-comparison.component.html',
  styleUrl: './leadership-comparison.component.scss',
})
export class LeadershipComparisonComponent {
  readonly rows: ComparisonRow[] = [
    {
      dimension: 'Organizational context',
      stateless: 'Starts from the prompt and general model knowledge.',
      dream: 'Uses approved architecture, runbooks, incidents, tests, and code evidence.',
    },
    {
      dimension: 'Ambiguity handling',
      stateless: 'Often fills gaps with plausible assumptions.',
      dream: 'Creates role-specific questions and preserves unresolved decisions.',
    },
    {
      dimension: 'Impact analysis',
      stateless: 'Suggests generic components and test areas.',
      dream: 'Binds the request to concrete files, historical risks, and test references.',
    },
    {
      dimension: 'Trust and review',
      stateless: 'The reviewer must reconstruct why the answer was produced.',
      dream: 'Shows source proof, selection reasons, governance status, eval, and audit.',
    },
  ];
}
