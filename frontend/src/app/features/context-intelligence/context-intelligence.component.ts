// SPDX-License-Identifier: Apache-2.0

import { DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';

import {
  ContextEvidence,
  ContextIntelligenceStatus,
  ContextPackSection,
} from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-context-intelligence',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './context-intelligence.component.html',
  styleUrl: './context-intelligence.component.scss',
})
export class ContextIntelligenceComponent {
  private readonly dream = inject(MockDreamService);

  readonly snapshot = this.dream.getContextIntelligenceSnapshot();
  readonly selectedSectionId = signal(this.snapshot.contextPackSections[0]?.id ?? '');

  readonly selectedSection = computed<ContextPackSection | null>(
    () => this.snapshot.contextPackSections.find((section) => section.id === this.selectedSectionId()) ?? null,
  );

  readonly selectedEvidence = computed<ContextEvidence[]>(() => {
    const section = this.selectedSection();
    if (!section) {
      return this.snapshot.evidenceCards;
    }
    const sectionEvidence = this.snapshot.evidenceCards.filter((card) =>
      section.includedEvidenceIds.includes(card.evidenceId),
    );
    return sectionEvidence.length ? sectionEvidence : this.snapshot.evidenceCards;
  });

  readonly promptText = computed(
    () => `${this.snapshot.promptPreview.system}

${this.snapshot.promptPreview.developer}

User request:
${this.snapshot.promptPreview.user}

Evidence instructions:
${this.snapshot.promptPreview.evidenceInstructions.map((instruction) => `- ${instruction}`).join('\n')}`,
  );

  selectSection(sectionId: string): void {
    this.selectedSectionId.set(sectionId);
  }

  statusClass(status: ContextIntelligenceStatus): string {
    switch (status) {
      case 'pass':
        return 'status-success';
      case 'watch':
        return 'status-warning';
      case 'needs_review':
        return 'status-error';
    }
  }

  formatStatus(status: ContextIntelligenceStatus): string {
    return status.replaceAll('_', ' ');
  }
}
