// SPDX-License-Identifier: Apache-2.0

import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';

import { KnowledgeIntakeItem, KnowledgeIntakeQueueStatus, KnowledgeIntakeReviewStatus } from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-knowledge-intake',
  standalone: true,
  imports: [DatePipe, DecimalPipe],
  templateUrl: './knowledge-intake.component.html',
  styleUrl: './knowledge-intake.component.scss',
})
export class KnowledgeIntakeComponent {
  private readonly dream = inject(MockDreamService);

  readonly queue = signal<KnowledgeIntakeItem[]>(this.dream.listKnowledgeIntakeQueue());
  readonly selectedItem = signal<KnowledgeIntakeItem | null>(this.queue()[0] ?? null);
  readonly actionMessage = signal('Select a source row, approve parsed sections, then promote approved knowledge to a pack.');

  readonly intakeMetrics = computed(() => [
    { label: 'Imports', value: this.queue().length, note: 'runbook + docx + HLD' },
    { label: 'Parsed sections', value: this.queue().reduce((total, item) => total + item.sections.length, 0), note: 'ready to review' },
    {
      label: 'Needs review',
      value: this.queue().filter((item) => item.reviewStatus === 'needs_review' || item.reviewStatus === 'unreviewed').length,
      note: 'human gate',
    },
    {
      label: 'Promoted',
      value: this.queue().filter((item) => item.reviewStatus === 'promoted').length,
      note: 'mock pack state',
    },
  ]);

  selectItem(item: KnowledgeIntakeItem): void {
    this.selectedItem.set(item);
  }

  approveSelected(): void {
    const item = this.selectedItem();
    if (!item || item.reviewStatus === 'promoted') {
      return;
    }
    this.updateItem(item.id, {
      queueStatus: 'ready_for_review',
      reviewStatus: 'approved',
      reviewNotes: ['Mock approval recorded by Knowledge Steward. Parsed sections are ready for promotion.'],
    });
    this.actionMessage.set(`${item.title} approved for ${item.targetPack}.`);
  }

  promoteSelected(): void {
    const item = this.selectedItem();
    if (!item || item.reviewStatus !== 'approved') {
      return;
    }
    this.updateItem(item.id, {
      queueStatus: 'promoted',
      reviewStatus: 'promoted',
      reviewNotes: ['Mock promotion completed. New chunks will be available to retrieval after backend integration.'],
    });
    this.actionMessage.set(`${item.title} promoted into ${item.targetPack}.`);
  }

  reparseSelected(): void {
    const item = this.selectedItem();
    if (!item || item.reviewStatus === 'promoted') {
      return;
    }
    this.updateItem(item.id, {
      queueStatus: 'parsing',
      reviewStatus: 'unreviewed',
      reviewNotes: ['Mock re-parse queued with the same deterministic source content.'],
    });
    this.actionMessage.set(`${item.title} moved back to parser queue.`);
  }

  statusClass(status: KnowledgeIntakeQueueStatus | KnowledgeIntakeReviewStatus): string {
    switch (status) {
      case 'approved':
      case 'parsed':
      case 'promoted':
      case 'ready_for_review':
        return 'status-success';
      case 'needs_review':
      case 'unreviewed':
      case 'queued':
      case 'parsing':
        return 'status-warning';
      default:
        return 'status-neutral';
    }
  }

  sourceKindLabel(item: KnowledgeIntakeItem): string {
    switch (item.sourceKind) {
      case 'runbook':
        return 'Runbook';
      case 'docx':
        return 'DOCX';
      case 'confluence_hld':
        return 'Confluence HLD';
    }
  }

  formatStatus(status: string): string {
    return status.replaceAll('_', ' ');
  }

  private updateItem(
    itemId: string,
    updates: Pick<KnowledgeIntakeItem, 'queueStatus' | 'reviewStatus' | 'reviewNotes'>,
  ): void {
    const updatedQueue = this.queue().map((item) => (item.id === itemId ? { ...item, ...updates } : item));
    this.queue.set(updatedQueue);
    this.selectedItem.set(updatedQueue.find((item) => item.id === itemId) ?? null);
  }
}
