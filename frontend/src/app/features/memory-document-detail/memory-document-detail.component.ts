// SPDX-License-Identifier: Apache-2.0

import { Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map } from 'rxjs';

import {
  DreamApiService,
  DraftReviewEvent,
  IntakeDocumentDetail,
  ParsedSection,
  SourceSpan,
} from '../../core/dream-api.service';

@Component({
  selector: 'app-memory-document-detail',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './memory-document-detail.component.html',
  styleUrl: './memory-document-detail.component.scss',
})
export class MemoryDocumentDetailComponent {
  private readonly api = inject(DreamApiService);
  private readonly route = inject(ActivatedRoute);

  readonly detail = signal<IntakeDocumentDetail | null>(null);
  readonly isLoading = signal(false);
  readonly apiError = signal<string | null>(null);
  readonly documentId = toSignal(
    this.route.paramMap.pipe(map((params) => params.get('documentId') ?? '')),
    { initialValue: this.route.snapshot.paramMap.get('documentId') ?? '' },
  );

  readonly draft = computed(() => this.detail()?.draft ?? null);
  readonly parsedSections = computed(() => this.draft()?.sections ?? []);
  readonly auditEvents = computed(() => this.detail()?.auditEvents ?? []);
  readonly reviewEvents = computed(() => this.detail()?.reviewEvents ?? []);
  readonly downstreamEvents = computed(() => this.detail()?.downstreamEvents ?? []);
  readonly downstreamUsages = computed(() => this.detail()?.downstreamUsages ?? []);

  constructor() {
    effect(() => {
      const documentId = this.documentId();
      if (documentId) {
        this.loadDetail(documentId);
      }
    });
  }

  loadDetail(documentId = this.documentId()): void {
    if (!documentId) {
      return;
    }
    this.isLoading.set(true);
    this.apiError.set(null);
    this.api.getIntakeDocumentDetail(documentId).subscribe({
      next: (detail) => {
        this.detail.set(detail);
        this.isLoading.set(false);
      },
      error: (error: unknown) => {
        this.apiError.set(error instanceof Error ? error.message : 'Source detail could not be loaded.');
        this.isLoading.set(false);
      },
    });
  }

  formatLabel(value: string | null | undefined): string {
    return (value || 'unknown')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  statusClass(status: string | null | undefined): string {
    if (['approved', 'completed', 'pass', 'promoted', 'success'].includes(status || '')) {
      return 'status-success';
    }
    if (['failed', 'fail'].includes(status || '')) {
      return 'status-error';
    }
    if (['parsed', 'pending_review', 'uploaded', 'warning', 'needs_review'].includes(status || '')) {
      return 'status-warning';
    }
    return 'status-info';
  }

  verificationLabel(value: boolean | null | undefined): string {
    if (value === true) {
      return 'Verified';
    }
    if (value === false) {
      return 'Hash mismatch';
    }
    return 'Not checked';
  }

  verificationClass(value: boolean | null | undefined): string {
    if (value === true) {
      return 'status-success';
    }
    if (value === false) {
      return 'status-error';
    }
    return 'status-neutral';
  }

  shortHash(value: string | null | undefined): string {
    if (!value) {
      return 'unknown';
    }
    const [, digest = value] = value.split(':');
    return `sha256:${digest.slice(0, 12)}`;
  }

  sectionSpan(section: ParsedSection): string {
    return this.spanLabel(section.sourceSpan);
  }

  spanLabel(span: SourceSpan | null | undefined): string {
    if (!span) {
      return 'No source span';
    }
    return `L${span.startLine ?? '?'}-L${span.endLine ?? '?'}`;
  }

  sizeLabel(bytes: number): string {
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${bytes} B`;
  }

  sourceFileName(sourcePath: string): string {
    const normalized = sourcePath.replace(/\\/g, '/');
    return normalized.split('/').filter(Boolean).at(-1) || sourcePath;
  }

  reviewEventTitle(event: DraftReviewEvent): string {
    return `${this.formatLabel(event.eventType)} / ${this.formatLabel(event.newStatus)}`;
  }

  diffValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'none';
    }
    if (Array.isArray(value)) {
      return value.length ? value.join(', ') : 'none';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  }
}
