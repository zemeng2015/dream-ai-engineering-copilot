// SPDX-License-Identifier: Apache-2.0

import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-codebase-summary-cards',
  standalone: true,
  templateUrl: './codebase-summary-cards.component.html',
  styleUrl: './codebase-summary-cards.component.scss',
})
export class CodebaseSummaryCardsComponent {
  @Input() indexedFiles = 0;
  @Input() sourceFiles = 0;
  @Input() testFiles = 0;
  @Input() symbols = 0;
  @Input() concepts = 0;
}
