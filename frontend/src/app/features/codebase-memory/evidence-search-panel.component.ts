// SPDX-License-Identifier: Apache-2.0

import { Component, EventEmitter, Input, Output } from '@angular/core';

import { CodebaseSearchItem } from '../../core/dream-api.service';

@Component({
  selector: 'app-evidence-search-panel',
  standalone: true,
  templateUrl: './evidence-search-panel.component.html',
  styleUrl: './evidence-search-panel.component.scss',
})
export class EvidenceSearchPanelComponent {
  @Input() results: CodebaseSearchItem[] = [];
  @Input() query = '';

  @Output() readonly sourceSelected = new EventEmitter<string>();

  scoreLabel(score: number): string {
    return Number(score.toFixed(1)).toString();
  }
}
