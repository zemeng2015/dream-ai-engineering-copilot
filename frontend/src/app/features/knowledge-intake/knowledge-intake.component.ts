// SPDX-License-Identifier: Apache-2.0

import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';

import {
  KnowledgeIntakeItem,
  KnowledgeIntakeQueueStatus,
  KnowledgeIntakeReviewStatus,
  KnowledgeIntakeSection,
  KnowledgeIntakeSourceKind,
} from '../../core/dream-models';
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
  readonly uploadMessage = signal('Choose a raw runbook, DOCX export, or Confluence HLD export to create a reviewable source.');
  readonly selectedUploadFileName = signal('No file selected');
  readonly reviewComment = signal('Sections match the status-tracking workflow and are safe to promote after steward review.');

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
    this.reviewComment.set('');
  }

  async onSourceUpload(event: Event): Promise<void> {
    const input = event.target instanceof HTMLInputElement ? event.target : null;
    const file = input?.files?.[0];
    if (!file) {
      return;
    }

    this.uploadMessage.set(`Uploading ${file.name}...`);
    this.selectedUploadFileName.set(file.name);
    const text = await file.text();
    const item = buildUploadedIntakeItem(file, text);
    this.queue.update((queue) => [item, ...queue]);
    this.selectedItem.set(item);
    this.reviewComment.set('Verified headings and task-status concepts; approve for demo knowledge pack.');
    this.actionMessage.set(`${item.title} uploaded and parsed into ${item.sections.length} reviewable sections.`);
    this.uploadMessage.set(`${file.name} parsed into ${item.sections.length} sections and is waiting for human review.`);
    input.value = '';
  }

  updateReviewComment(event: Event): void {
    const value = event.target instanceof HTMLTextAreaElement ? event.target.value : '';
    this.reviewComment.set(value);
  }

  approveSelected(): void {
    const item = this.selectedItem();
    if (!item || item.reviewStatus === 'promoted') {
      return;
    }
    const comment = this.normalizedReviewComment('Approval recorded by Knowledge Steward.');
    this.updateItem(item.id, {
      queueStatus: 'ready_for_review',
      reviewStatus: 'approved',
      reviewNotes: [
        `Approval comment by Knowledge Steward: ${comment}`,
        ...item.reviewNotes,
      ],
    });
    this.actionMessage.set(`${item.title} approved for ${item.targetPack}.`);
  }

  promoteSelected(): void {
    const item = this.selectedItem();
    if (!item || item.reviewStatus !== 'approved') {
      return;
    }
    const comment = this.normalizedReviewComment('Promoted after approved human review.');
    this.updateItem(item.id, {
      queueStatus: 'promoted',
      reviewStatus: 'promoted',
      reviewNotes: [
        `Promotion comment: ${comment}`,
        ...item.reviewNotes,
      ],
      promotionSummary: `${item.sections.length} reviewed sections promoted to ${item.targetPack}.`,
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
    updates: Partial<Pick<KnowledgeIntakeItem, 'queueStatus' | 'reviewStatus' | 'reviewNotes' | 'promotionSummary'>>,
  ): void {
    const updatedQueue = this.queue().map((item) => (item.id === itemId ? { ...item, ...updates } : item));
    this.queue.set(updatedQueue);
    this.selectedItem.set(updatedQueue.find((item) => item.id === itemId) ?? null);
  }

  private normalizedReviewComment(fallback: string): string {
    return this.reviewComment().trim() || fallback;
  }
}

function buildUploadedIntakeItem(file: File, text: string): KnowledgeIntakeItem {
  const sections = parseSections(text);
  const concepts = unique(sections.flatMap((section) => section.concepts));
  const sourceKind = inferSourceKind(file.name, text);
  const targetPack = sourceKind === 'confluence_hld'
    ? 'demo_team/architecture'
    : sourceKind === 'docx'
      ? 'demo_team/domain'
      : 'demo_team/runbooks';

  return {
    id: `upload-${Date.now().toString(36)}`,
    title: titleFromFileName(file.name),
    sourceKind,
    sourcePath: `uploaded://${file.name}`,
    owner: 'Demo Steward',
    importedAt: new Date().toISOString(),
    queueStatus: 'parsed',
    reviewStatus: 'needs_review',
    targetPack,
    parser: 'deterministic-local-parser-v1',
    parsedConcepts: concepts,
    sections,
    reviewNotes: [`Uploaded ${file.name} and parsed locally. Human review is required before promotion.`],
    promotionSummary: `Pending approval for ${targetPack}.`,
  };
}

function parseSections(text: string): KnowledgeIntakeSection[] {
  const normalized = text.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').trim();
  const blocks = normalized
    ? normalized.split(/\n(?=#{1,3}\s)|\n{2,}/).map((block) => block.trim()).filter(Boolean)
    : ['Empty source document'];
  return blocks.slice(0, 5).map((block, index) => {
    const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
    const rawHeading = lines[0] ?? `Section ${index + 1}`;
    const heading = rawHeading.replace(/^#{1,3}\s*/, '') || `Section ${index + 1}`;
    const body = lines.slice(rawHeading.startsWith('#') ? 1 : 0).join(' ') || heading;
    const concepts = inferConcepts(`${heading} ${body}`);
    return {
      id: `uploaded-section-${index + 1}`,
      heading,
      summary: summarize(body),
      concepts,
      confidence: Math.min(0.94, 0.76 + concepts.length * 0.035),
    };
  });
}

function inferSourceKind(fileName: string, text: string): KnowledgeIntakeSourceKind {
  const lowerName = fileName.toLowerCase();
  const lowerText = text.toLowerCase();
  if (lowerName.endsWith('.docx')) {
    return 'docx';
  }
  if (lowerText.includes('confluence') || lowerText.includes('hld') || lowerName.includes('hld')) {
    return 'confluence_hld';
  }
  return 'runbook';
}

function inferConcepts(text: string): string[] {
  const lower = text.toLowerCase();
  const concepts = [
    { concept: 'execution status', terms: ['status', 'running', 'queued', 'completed', 'partial'] },
    { concept: 'operator runbook', terms: ['runbook', 'operator', 'escalation', 'rollback'] },
    { concept: 'task progress', terms: ['task', 'progress', 'step', 'workflow'] },
    { concept: 'stuck running', terms: ['stuck', 'timeout', 'stale', 'long-running'] },
    { concept: 'human review', terms: ['review', 'approval', 'approve', 'steward'] },
    { concept: 'api contract', terms: ['api', 'endpoint', 'payload', 'contract'] },
    { concept: 'test coverage', terms: ['test', 'coverage', 'regression', 'scenario'] },
  ]
    .filter((candidate) => candidate.terms.some((term) => lower.includes(term)))
    .map((candidate) => candidate.concept);
  return concepts.length ? unique(concepts).slice(0, 5) : ['source intake', 'human review'];
}

function summarize(text: string): string {
  const compact = text.replace(/\s+/g, ' ').trim();
  if (compact.length <= 190) {
    return compact;
  }
  return `${compact.slice(0, 187).trimEnd()}...`;
}

function titleFromFileName(fileName: string): string {
  return fileName
    .replace(/\.[^.]+$/, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}
