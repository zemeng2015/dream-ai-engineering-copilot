// SPDX-License-Identifier: Apache-2.0

import { Component, EventEmitter, Input, Output } from '@angular/core';

import { CodebaseConcept } from '../../core/dream-api.service';

@Component({
  selector: 'app-impact-map-panel',
  standalone: true,
  templateUrl: './impact-map-panel.component.html',
  styleUrl: './impact-map-panel.component.scss',
})
export class ImpactMapPanelComponent {
  @Input() concepts: CodebaseConcept[] = [];

  @Output() readonly sourceSelected = new EventEmitter<string>();

  conceptCountLabel(concept: CodebaseConcept): string {
    const fileCount = concept.relatedFiles.length;
    const testCount = concept.relatedTests.length;
    return `${fileCount} files / ${testCount} tests`;
  }

  fileName(path: string): string {
    return path.split('/').pop() || path;
  }
}
