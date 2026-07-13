// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { DreamApiService, MemoryClaimSource } from '../../core/dream-api.service';

@Component({
  selector: 'app-memory-claim-source-review',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './memory-claim-source-review.component.html',
  styleUrl: './memory-claim-source-review.component.scss',
})
export class MemoryClaimSourceReviewComponent {
  private readonly api = inject(DreamApiService);
  private readonly route = inject(ActivatedRoute);

  readonly source = signal<MemoryClaimSource | null>(null);
  readonly isLoading = signal(false);
  readonly apiError = signal<string | null>(null);
  readonly sourceLines = computed(() => this.source()?.content.split(/\r?\n/) ?? []);

  constructor() {
    this.loadSource();
  }

  loadSource(): void {
    const params = this.route.snapshot.queryParamMap;
    const teamId = params.get('teamId') ?? '';
    const scanId = params.get('scanId') ?? '';
    const claimId = params.get('claimId') ?? '';
    const sourcePath = params.get('sourcePath') ?? '';
    if (!teamId || !scanId || !claimId || !sourcePath) {
      this.apiError.set('Claim source review requires team, scan, claim, and source identifiers.');
      return;
    }

    this.isLoading.set(true);
    this.apiError.set(null);
    this.api.getMemoryClaimSource(teamId, scanId, claimId, sourcePath).subscribe({
      next: (source) => {
        this.source.set(source);
        this.isLoading.set(false);
      },
      error: (error: unknown) => {
        this.apiError.set(error instanceof Error ? error.message : 'Claim source could not be loaded.');
        this.isLoading.set(false);
      },
    });
  }

  isEvidenceLine(lineNumber: number): boolean {
    return (
      this.source()?.spans.some((span) => {
        if (span.startLine == null && span.endLine == null) return false;
        const start = span.startLine ?? span.endLine ?? lineNumber;
        const end = span.endLine ?? span.startLine ?? lineNumber;
        return lineNumber >= start && lineNumber <= end;
      }) ?? false
    );
  }

  spanLabel(startLine?: number | null, endLine?: number | null): string {
    if (startLine == null && endLine == null) return 'Line range unavailable';
    return `L${startLine ?? endLine}-L${endLine ?? startLine}`;
  }

  shortHash(value: string): string {
    const [, digest = value] = value.split(':');
    return `sha256:${digest.slice(0, 12)}`;
  }

  sizeLabel(bytes: number): string {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  }
}
