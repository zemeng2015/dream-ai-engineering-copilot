// SPDX-License-Identifier: Apache-2.0

import { Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, forkJoin, map, of } from 'rxjs';

import { DreamApiService } from '../../core/dream-api.service';
import type {
  ContextEvidenceCandidate,
  ContextPack,
  ContextPromptPreview,
  ContextRetrievalTrail,
  IntakeDocument,
} from '../../core/dream-api.service';
import { sourceDocumentRoute as routeForSourceDocument } from '../../core/source-provenance';
import { UiIconComponent } from '../../shared/ui-icon.component';

interface EvidenceGroup {
  label: string;
  items: ContextEvidenceCandidate[];
}

@Component({
  selector: 'app-context-detail',
  standalone: true,
  imports: [RouterLink, UiIconComponent],
  templateUrl: './context-detail.component.html',
  styleUrl: './context-detail.component.scss',
})
export class ContextDetailComponent {
  private readonly api = inject(DreamApiService);
  private readonly route = inject(ActivatedRoute);

  readonly caseId = toSignal(
    this.route.paramMap.pipe(map((params) => params.get('caseId') ?? '')),
    { initialValue: this.route.snapshot.paramMap.get('caseId') ?? '' },
  );

  readonly trail = signal<ContextRetrievalTrail | null>(null);
  readonly pack = signal<ContextPack | null>(null);
  readonly preview = signal<ContextPromptPreview | null>(null);
  readonly intakeDocuments = signal<IntakeDocument[]>([]);
  readonly isLoading = signal(false);
  readonly apiError = signal<string | null>(null);

  readonly evidenceGroups = computed<EvidenceGroup[]>(() => {
    const pack = this.pack();
    if (!pack) {
      return [];
    }
    return [
      { label: 'Docs', items: pack.selectedDocs },
      { label: 'Code', items: pack.selectedCode },
      { label: 'Tests', items: pack.selectedTests },
      { label: 'Incidents', items: pack.selectedIncidents },
      { label: 'Historical Jira', items: pack.selectedHistoricalJira },
      { label: 'Historical PR', items: pack.selectedHistoricalPr },
    ].filter((group) => group.items.length);
  });

  constructor() {
    effect(() => {
      const caseId = this.caseId();
      if (caseId) {
        this.loadContext(caseId);
      }
    });
  }

  loadContext(caseId = this.caseId()): void {
    if (!caseId) {
      return;
    }
    this.isLoading.set(true);
    this.apiError.set(null);
    forkJoin({
      trail: this.api.getContextTrail(caseId),
      pack: this.api.getContextPack(caseId),
      preview: this.api.getContextPromptPreview(caseId),
      intakeDocuments: this.api.listIntakeDocuments().pipe(catchError(() => of([]))),
    }).subscribe({
      next: ({ trail, pack, preview, intakeDocuments }) => {
        this.trail.set(trail);
        this.pack.set(pack);
        this.preview.set(preview);
        this.intakeDocuments.set(intakeDocuments);
        this.isLoading.set(false);
      },
      error: (error: unknown) => {
        this.apiError.set(error instanceof Error ? error.message : 'Context detail could not be loaded.');
        this.isLoading.set(false);
      },
    });
  }

  sourceDocumentRoute(sourcePath: string): string[] | null {
    return routeForSourceDocument(sourcePath, this.intakeDocuments());
  }

  sourceFileName(sourcePath: string): string {
    const normalized = sourcePath.split('#')[0].replace(/\\/g, '/');
    return normalized.split('/').filter(Boolean).at(-1) || sourcePath;
  }

  formatLabel(value: string | null | undefined): string {
    return (value || 'unknown')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  statusClass(value: string | boolean | null | undefined): string {
    if (value === true || ['selected', 'approved', 'pass', 'completed'].includes(String(value))) {
      return 'status-success';
    }
    if (['candidate', 'watch', 'warning', 'needs_review'].includes(String(value))) {
      return 'status-warning';
    }
    return 'status-info';
  }

  scoreLabel(score: number): string {
    return Number(score.toFixed(2)).toString();
  }

  shortHash(value: string | null | undefined): string {
    if (!value) {
      return 'hash unknown';
    }
    return value.replace(/^sha256:/, '').slice(0, 12);
  }
}
