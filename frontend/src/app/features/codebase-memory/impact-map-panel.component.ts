// SPDX-License-Identifier: Apache-2.0

import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CodebaseConcept } from '../../core/dream-api.service';

@Component({
  selector: 'app-impact-map-panel',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './impact-map-panel.component.html',
  styleUrl: './impact-map-panel.component.scss',
})
export class ImpactMapPanelComponent {
  @Input() concepts: CodebaseConcept[] = [];
  @Input() selectedFilePath: string | null = null;

  @Output() readonly sourceSelected = new EventEmitter<string>();

  conceptCountLabel(concept: CodebaseConcept): string {
    const fileCount = concept.relatedFiles.length;
    const testCount = concept.relatedTests.length;
    return `${fileCount} files / ${testCount} tests`;
  }

  conceptScopeLabel(): string {
    if (this.selectedFilePath) {
      return `${this.concepts.length} concepts linked to the selected file`;
    }
    return `${this.concepts.length} top concepts across this repository`;
  }

  fileName(path: string): string {
    return path.split('/').pop() || path;
  }
}
