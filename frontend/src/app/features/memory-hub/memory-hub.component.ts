// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, forkJoin, of, switchMap } from 'rxjs';

import {
  CodebaseIndexFile,
  DreamApiService,
  IntakeDocument,
  KnowledgeDraft,
  MemoryClaim,
  MemoryConflictClaimSide,
  MemoryConflictPair,
  MemoryConflictReport,
  MemoryConflictResolutionLedger,
  MemoryDiffResult,
  MemoryLedgerSnapshot,
  MemoryReviewEvent,
  MemoryScanResult,
} from '../../core/dream-api.service';
import { UiIconComponent } from '../../shared/ui-icon.component';

type MemoryTab = 'sources' | 'claims' | 'codebase';
type ClaimChangeType = 'added' | 'changed' | 'existing';

interface MemoryTabItem {
  id: MemoryTab;
  label: string;
  count: number | string;
  note: string;
  status: string;
  tone: 'info' | 'warning' | 'success';
}

interface MemoryClaimReviewRow {
  claim: MemoryClaim;
  changeType: ClaimChangeType;
  effectiveStatus: string;
  latestReview?: MemoryReviewEvent;
}

@Component({
  selector: 'app-memory-hub',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, UiIconComponent],
  templateUrl: './memory-hub.component.html',
  styleUrl: './memory-hub.component.scss',
})
export class MemoryHubComponent {
  private readonly api = inject(DreamApiService);
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);

  readonly isLoading = signal(false);
  readonly uploadInFlight = signal(false);
  readonly sourceActionInFlight = signal<string | null>(null);
  readonly claimReviewInFlight = signal<string | null>(null);
  readonly conflictResolveInFlight = signal<string | null>(null);
  readonly scanInFlight = signal(false);
  readonly apiError = signal<string | null>(null);
  readonly uploadMessage = signal<string | null>(null);
  readonly selectedSourceFile = signal<File | null>(null);
  readonly selectedSourceFileName = signal('No file selected');
  readonly metadataInFlight = signal(false);
  readonly selectedMetadataDocument = signal<IntakeDocument | null>(null);
  readonly selectedKnowledgeDraft = signal<KnowledgeDraft | null>(null);
  readonly intakeDocuments = signal<IntakeDocument[]>([]);
  readonly codebaseFiles = signal<CodebaseIndexFile[]>([]);
  readonly memoryDiff = signal<MemoryDiffResult | null>(null);
  readonly memoryConflicts = signal<MemoryConflictReport | null>(null);
  readonly memoryConflictResolutions = signal<MemoryConflictResolutionLedger | null>(null);
  readonly memoryScan = signal<MemoryScanResult | null>(null);
  readonly memoryLedger = signal<MemoryLedgerSnapshot | null>(null);
  readonly activeTab = signal<MemoryTab>(this.initialTab());
  readonly claimPage = signal(1);
  readonly claimPageSize = signal(20);

  readonly uploadForm = this.fb.nonNullable.group({
    teamId: ['demo_team', Validators.required],
    filePath: [''],
    documentType: ['runbooks', Validators.required],
    title: [''],
  });

  readonly metadataForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    documentType: ['runbooks', Validators.required],
    app: [''],
    component: [''],
    concepts: [''],
  });

  readonly sourceReviewQueue = computed(() =>
    this.intakeDocuments().filter((item) => !this.sourceInMemory(item)),
  );
  readonly approvedSourceItems = computed(() =>
    this.intakeDocuments().filter((item) => this.sourceInMemory(item)),
  );
  readonly linkedTestFiles = computed(() =>
    this.codebaseFiles().filter((file) => file.role === 'test').length,
  );
  readonly sourceCodeFiles = computed(() =>
    this.codebaseFiles().filter((file) => file.role === 'source').length,
  );
  readonly latestReviewByClaim = computed(() => {
    const latest = new Map<string, MemoryReviewEvent>();
    for (const event of this.memoryLedger()?.events ?? []) {
      latest.set(event.claimId, event);
    }
    return latest;
  });
  readonly claimReviewRows = computed<MemoryClaimReviewRow[]>(() => {
    const diff = this.memoryDiff();
    const scan = this.memoryScan();
    if (!scan && !diff) {
      return [];
    }
    const changeTypeByClaim = new Map<string, ClaimChangeType>();
    for (const claim of diff?.addedClaims ?? []) {
      changeTypeByClaim.set(claim.claimId, 'added');
    }
    for (const claim of diff?.changedClaims ?? []) {
      changeTypeByClaim.set(claim.claimId, 'changed');
    }
    const latest = this.latestReviewByClaim();
    const claims =
      scan?.claims ??
      [...(diff?.addedClaims ?? []), ...(diff?.changedClaims ?? [])];
    const rows = claims.map((claim) =>
      this.claimRow(
        claim,
        changeTypeByClaim.get(claim.claimId) ?? 'existing',
        latest.get(claim.claimId),
      ),
    );
    return rows.sort((a, b) => {
      const aCandidate = a.effectiveStatus === 'candidate' ? 0 : 1;
      const bCandidate = b.effectiveStatus === 'candidate' ? 0 : 1;
      const aProof = a.claim.evidence.intakeProofs.length ? 0 : 1;
      const bProof = b.claim.evidence.intakeProofs.length ? 0 : 1;
      return (
        aCandidate - bCandidate ||
        aProof - bProof ||
        a.claim.entity.canonicalName.localeCompare(b.claim.entity.canonicalName) ||
        a.claim.claimId.localeCompare(b.claim.claimId)
      );
    });
  });
  readonly reviewableClaimCount = computed(
    () => this.claimReviewRows().filter((row) => row.effectiveStatus === 'candidate').length,
  );
  readonly governedClaimCount = computed(
    () => this.claimReviewRows().length - this.reviewableClaimCount(),
  );
  readonly scanSourceCount = computed(
    () =>
      new Set(
        this.claimReviewRows().flatMap((row) => row.claim.evidence.sourceIds),
      ).size,
  );
  readonly claimTotalPages = computed(() =>
    Math.max(1, Math.ceil(this.claimReviewRows().length / this.claimPageSize())),
  );
  readonly pagedClaimReviewRows = computed(() => {
    const page = Math.min(this.claimPage(), this.claimTotalPages());
    const start = (page - 1) * this.claimPageSize();
    return this.claimReviewRows().slice(start, start + this.claimPageSize());
  });
  readonly claimRangeStart = computed(() =>
    this.claimReviewRows().length ? (this.claimPage() - 1) * this.claimPageSize() + 1 : 0,
  );
  readonly claimRangeEnd = computed(() =>
    Math.min(this.claimPage() * this.claimPageSize(), this.claimReviewRows().length),
  );
  readonly conflictPairCount = computed(() => this.memoryConflicts()?.conflictCount ?? 0);

  readonly memoryTabs = computed<MemoryTabItem[]>(() => [
    {
      id: 'sources',
      label: 'Source Intake',
      count: this.intakeDocuments().length,
      note: `${this.intakeDocuments().length} new submissions / ${this.scanSourceCount()} scanned sources`,
      status: this.sourceReviewQueue().length ? 'Review pending' : 'Current',
      tone: this.sourceReviewQueue().length ? 'warning' : 'success',
    },
    {
      id: 'claims',
      label: 'Claim Review',
      count: this.claimReviewRows().length,
      note: `${this.reviewableClaimCount()} awaiting decision / ${this.governedClaimCount()} governed`,
      status: this.reviewableClaimCount() || this.conflictPairCount() ? 'Needs review' : 'Current',
      tone: this.reviewableClaimCount() || this.conflictPairCount() ? 'warning' : 'success',
    },
    {
      id: 'codebase',
      label: 'Codebase Index',
      count: this.codebaseFiles().length,
      note: `${this.linkedTestFiles()} tests linked`,
      status: 'Indexed',
      tone: 'info',
    },
  ]);

  constructor() {
    this.loadMemory();
  }

  loadMemory(): void {
    this.isLoading.set(true);
    this.apiError.set(null);
    forkJoin({
      intakeDocuments: this.api.listIntakeDocuments().pipe(catchError(() => of([]))),
      codebaseFiles: this.api.listCodebaseFiles('demo_team', 'dfp-demo-repo').pipe(catchError(() => of([]))),
      memoryScan: this.api.getLatestMemoryScan('demo_team').pipe(catchError(() => of(null))),
      memoryDiff: this.api.getMemoryDiff('demo_team').pipe(catchError(() => of(null))),
      memoryConflicts: this.api.getMemoryConflicts('demo_team').pipe(catchError(() => of(null))),
      memoryConflictResolutions: this.api
        .getMemoryConflictResolutions('demo_team')
        .pipe(catchError(() => of(null))),
      memoryLedger: this.api.getMemoryLedger('demo_team').pipe(catchError(() => of(null))),
    }).subscribe({
      next: ({
        intakeDocuments,
        codebaseFiles,
        memoryScan,
        memoryDiff,
        memoryConflicts,
        memoryConflictResolutions,
        memoryLedger,
      }) => {
        this.intakeDocuments.set(intakeDocuments);
        this.codebaseFiles.set(codebaseFiles);
        this.memoryScan.set(memoryScan);
        this.memoryDiff.set(memoryDiff);
        this.memoryConflicts.set(memoryConflicts);
        this.memoryConflictResolutions.set(memoryConflictResolutions);
        this.memoryLedger.set(memoryLedger);
        this.setClaimPage(this.claimPage());
        this.isLoading.set(false);
      },
      error: () => {
        this.apiError.set('FastAPI memory data could not be loaded.');
        this.isLoading.set(false);
      },
    });
  }

  registerSource(): void {
    const value = this.uploadForm.getRawValue();
    const selectedFile = this.selectedSourceFile();
    const filePath = value.filePath.trim();
    if (this.uploadForm.invalid || (!selectedFile && !filePath)) {
      this.uploadForm.markAllAsTouched();
      this.apiError.set('Choose a file or enter a backend-visible file path.');
      return;
    }
    this.uploadInFlight.set(true);
    this.uploadMessage.set(null);
    this.apiError.set(null);
    const request = selectedFile
      ? this.api.uploadIntakeFile({
          teamId: value.teamId,
          file: selectedFile,
          documentType: value.documentType,
          title: value.title.trim() || undefined,
        })
      : this.api.uploadIntakeDocument({
          teamId: value.teamId,
          filePath,
          documentType: value.documentType,
          title: value.title.trim() || undefined,
        });
    request.subscribe({
      next: (document) => {
        this.intakeDocuments.update((items) => [
          document,
          ...items.filter((item) => item.documentId !== document.documentId),
        ]);
        this.uploadMessage.set(`${selectedFile ? 'Uploaded' : 'Registered'} ${document.title}.`);
        this.selectedSourceFile.set(null);
        this.selectedSourceFileName.set('No file selected');
        this.uploadInFlight.set(false);
      },
      error: (error: unknown) => {
        this.apiError.set(error instanceof Error ? error.message : 'Source registration failed.');
        this.uploadInFlight.set(false);
      },
    });
  }

  onSourceFileSelected(event: Event): void {
    const input = event.target instanceof HTMLInputElement ? event.target : null;
    const file = input?.files?.[0] ?? null;
    this.selectedSourceFile.set(file);
    this.selectedSourceFileName.set(file?.name ?? 'No file selected');
  }

  sourceReviewSummary(item: IntakeDocument): string {
    return `${item.documentType} / ${this.sourceFileName(item)}`;
  }

  provenanceSummary(draft: KnowledgeDraft): string {
    const spanCount = draft.sections.filter((section) => section.sourceSpan).length;
    const hash = draft.sourceHash ? shortHash(draft.sourceHash) : 'source hash pending';
    return `${hash} / ${draft.sections.length} sections / ${spanCount} spans`;
  }

  sourceFileName(item: IntakeDocument): string {
    const path = this.sourceFullPath(item);
    return path.replace(/\\/g, '/').split('/').filter(Boolean).at(-1) || path;
  }

  sourceFullPath(item: IntakeDocument): string {
    return item.promotedPath || item.storedPath || item.originalPath;
  }

  sourceStatusClass(item: IntakeDocument): string {
    if (this.sourceInMemory(item)) {
      return 'status-success';
    }
    return 'status-warning';
  }

  sourceStatusLabel(status: string): string {
    return status.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  canEditMetadata(item: IntakeDocument): boolean {
    return item.status === 'parsed' || item.status === 'approved';
  }

  openMetadataEditor(item: IntakeDocument): void {
    if (!this.canEditMetadata(item)) {
      return;
    }
    this.metadataInFlight.set(true);
    this.apiError.set(null);
    this.selectedMetadataDocument.set(item);
    this.selectedKnowledgeDraft.set(null);
    this.api.getIntakeDraft(item.documentId).subscribe({
      next: (draft) => {
        this.selectedKnowledgeDraft.set(draft);
        this.metadataForm.setValue({
          title: draft.title,
          documentType: draft.targetDocType,
          app: draft.app ?? '',
          component: draft.component ?? '',
          concepts: draft.concepts.map((concept) => concept.concept).join(', '),
        });
        this.metadataInFlight.set(false);
      },
      error: (error: unknown) => {
        this.apiError.set(error instanceof Error ? error.message : 'Draft metadata could not be loaded.');
        this.metadataInFlight.set(false);
      },
    });
  }

  saveMetadata(): void {
    const item = this.selectedMetadataDocument();
    if (!item || this.metadataForm.invalid) {
      this.metadataForm.markAllAsTouched();
      return;
    }
    this.metadataInFlight.set(true);
    this.apiError.set(null);
    this.uploadMessage.set(null);
    const value = this.metadataForm.getRawValue();
    this.api
      .updateIntakeDraftMetadata(item.documentId, {
        title: value.title.trim(),
        targetDocType: value.documentType,
        app: value.app.trim(),
        component: value.component.trim(),
        concepts: splitConcepts(value.concepts),
        reviewer: 'Demo Reviewer',
        notes: 'Metadata updated from Memory Hub before review.',
      })
      .subscribe({
        next: (draft) => {
          this.selectedKnowledgeDraft.set(draft);
          this.intakeDocuments.update((items) =>
            items.map((source) =>
              source.documentId === draft.documentId
                ? {
                    ...source,
                    title: draft.title,
                    documentType: draft.targetDocType,
                  }
                : source,
            ),
          );
          this.selectedMetadataDocument.update((source) =>
            source
              ? {
                  ...source,
                  title: draft.title,
                  documentType: draft.targetDocType,
                }
              : source,
          );
          this.uploadMessage.set(`Metadata saved for ${draft.title}.`);
          this.metadataInFlight.set(false);
        },
        error: (error: unknown) => {
          this.apiError.set(error instanceof Error ? error.message : 'Metadata update failed.');
          this.metadataInFlight.set(false);
        },
      });
  }

  closeMetadataEditor(): void {
    this.selectedMetadataDocument.set(null);
    this.selectedKnowledgeDraft.set(null);
  }

  setActiveTab(tab: MemoryTab): void {
    this.activeTab.set(tab);
  }

  setClaimPage(page: number): void {
    const normalized = Number.isFinite(page) ? Math.trunc(page) : 1;
    this.claimPage.set(Math.min(Math.max(normalized, 1), this.claimTotalPages()));
  }

  setClaimPageSize(event: Event): void {
    const select = event.target instanceof HTMLSelectElement ? event.target : null;
    const pageSize = Number(select?.value ?? 20);
    this.claimPageSize.set([10, 20, 50].includes(pageSize) ? pageSize : 20);
    this.claimPage.set(1);
  }

  claimHasReviewSource(claim: MemoryClaim): boolean {
    return Boolean(claim.evidence.intakeProofs[0]?.documentId || claim.evidence.spans[0]?.path);
  }

  claimSourceRoute(claim: MemoryClaim): string[] {
    const proof = claim.evidence.intakeProofs[0];
    return proof?.documentId ? ['/memory', proof.documentId] : ['/memory/source'];
  }

  claimSourceQueryParams(claim: MemoryClaim): Record<string, string> | null {
    if (claim.evidence.intakeProofs[0]?.documentId) {
      return null;
    }
    const sourcePath = claim.evidence.spans[0]?.path;
    if (!sourcePath) {
      return null;
    }
    return {
      teamId: claim.teamId,
      scanId: claim.scanId,
      claimId: claim.claimId,
      sourcePath,
    };
  }

  runMemoryScan(): void {
    this.scanInFlight.set(true);
    this.apiError.set(null);
    this.uploadMessage.set(null);
    this.api
      .scanMemory({
        teamId: 'demo_team',
        repoPath: 'examples/dfp-demo-repo',
        repoName: 'dfp-demo-repo',
      })
      .pipe(
        switchMap((scan) =>
          forkJoin({
            scan: of(scan),
            diff: this.api.getMemoryDiff(scan.teamId, scan.scanId).pipe(catchError(() => of(null))),
            conflicts: this.api.getMemoryConflicts(scan.teamId, scan.scanId).pipe(catchError(() => of(null))),
            conflictResolutions: this.api
              .getMemoryConflictResolutions(scan.teamId)
              .pipe(catchError(() => of(null))),
            ledger: this.api.getMemoryLedger(scan.teamId).pipe(catchError(() => of(null))),
          }),
        ),
      )
      .subscribe({
        next: ({ scan, diff, conflicts, conflictResolutions, ledger }) => {
          this.memoryScan.set(scan);
          this.memoryDiff.set(diff);
          this.memoryConflicts.set(conflicts);
          this.memoryConflictResolutions.set(conflictResolutions);
          this.memoryLedger.set(ledger);
          this.claimPage.set(1);
          this.uploadMessage.set(`Memory scan ${scan.scanId} ready for review.`);
          this.scanInFlight.set(false);
        },
        error: (error: unknown) => {
          this.apiError.set(error instanceof Error ? error.message : 'Memory scan failed.');
          this.scanInFlight.set(false);
        },
      });
  }

  reviewClaim(row: MemoryClaimReviewRow, status: 'approved' | 'rejected' | 'quarantined'): void {
    const inFlightKey = `${row.claim.claimId}:${status}`;
    this.claimReviewInFlight.set(inFlightKey);
    this.apiError.set(null);
    this.uploadMessage.set(null);
    this.api
      .reviewMemoryClaim({
        teamId: row.claim.teamId,
        claimId: row.claim.claimId,
        status,
        reviewer: 'Demo Reviewer',
        reason: `Reviewed from Memory Hub claim review as ${status}.`,
        scanId: row.claim.scanId,
      })
      .subscribe({
        next: (event) => {
          this.memoryLedger.update((ledger) => {
            const current = ledger ?? { teamId: event.teamId, updatedAt: event.reviewedAt, events: [] };
            return {
              ...current,
              updatedAt: event.reviewedAt,
              events: [...current.events, event],
            };
          });
          this.uploadMessage.set(`${this.sourceStatusLabel(status)} ${row.claim.entity.canonicalName}.`);
          this.refreshMemoryConflicts(event.teamId, event.scanId);
          this.claimReviewInFlight.set(null);
        },
        error: (error: unknown) => {
          this.apiError.set(error instanceof Error ? error.message : 'Claim review failed.');
          this.claimReviewInFlight.set(null);
        },
      });
  }

  resolveConflict(pair: MemoryConflictPair, winningClaimId: string): void {
    const inFlightKey = `${pair.conflictId}:${winningClaimId}`;
    this.conflictResolveInFlight.set(inFlightKey);
    this.apiError.set(null);
    this.uploadMessage.set(null);
    this.api
      .resolveMemoryConflict({
        teamId: pair.teamId,
        scanId: pair.scanId,
        conflictId: pair.conflictId,
        winningClaimId,
        reviewer: 'Demo Reviewer',
        reason: `Resolved from Memory Hub by keeping ${winningClaimId}.`,
      })
      .subscribe({
        next: (event) => {
          this.memoryConflictResolutions.update((ledger) => {
            const current = ledger ?? { teamId: event.teamId, updatedAt: event.resolvedAt, events: [] };
            return {
              ...current,
              updatedAt: event.resolvedAt,
              events: [...current.events, event],
            };
          });
          this.uploadMessage.set(`Resolved conflict ${event.conflictId}.`);
          this.refreshMemoryReviewState(event.teamId, event.scanId);
          this.conflictResolveInFlight.set(null);
        },
        error: (error: unknown) => {
          this.apiError.set(error instanceof Error ? error.message : 'Conflict resolution failed.');
          this.conflictResolveInFlight.set(null);
        },
      });
  }

  resolveButtonBusy(pair: MemoryConflictPair, winningClaimId: string): boolean {
    const current = this.conflictResolveInFlight();
    return current === `${pair.conflictId}:${winningClaimId}` || current?.startsWith(`${pair.conflictId}:`) === true;
  }

  reviewButtonBusy(row: MemoryClaimReviewRow, status: string): boolean {
    const current = this.claimReviewInFlight();
    return current === `${row.claim.claimId}:${status}` || current?.startsWith(`${row.claim.claimId}:`) === true;
  }

  claimRelationValue(claim: MemoryClaim): string {
    return claim.relation.value || claim.relation.objectEntityId || 'No relation value';
  }

  claimEvidencePath(claim: MemoryClaim): string {
    return claim.evidence.spans.map((span) => span.path).join(', ') || 'No evidence path';
  }

  conflictSideStatusClass(side: MemoryConflictClaimSide): string {
    if (side.effectiveStatus === 'approved') {
      return 'status-success';
    }
    if (side.effectiveStatus === 'candidate') {
      return 'status-warning';
    }
    return 'status-info';
  }

  conflictSideSourceSummary(side: MemoryConflictClaimSide): string {
    if (side.intakeDocumentIds.length) {
      return side.intakeDocumentIds.join(', ');
    }
    return side.evidencePaths.join(', ') || 'No source trace';
  }

  reviewSignalSummary(review: MemoryReviewEvent): string {
    return this.reviewSignals(review).slice(0, 3).join(', ');
  }

  reviewSignals(review: MemoryReviewEvent): string[] {
    return [...review.riskSignals, ...review.conflictSignals];
  }

  reviewSignalClass(signal: string): string {
    if (signal.startsWith('potential_conflict') || signal.includes('unverified')) {
      return 'status-warning';
    }
    if (signal.startsWith('security_classification') || signal.startsWith('risk_level')) {
      return 'status-info';
    }
    return 'status-neutral';
  }

  reviewSignalLabel(signal: string): string {
    return signal.replace(/[_:]/g, ' ');
  }

  reviewValue(value: string | null | undefined): string {
    return value?.trim() || '_';
  }

  shortHash(value: string | null | undefined): string {
    if (!value) {
      return 'hash unknown';
    }
    const [, digest = value] = value.split(':');
    return `sha256:${digest.slice(0, 12)}`;
  }

  sourceActionLabel(item: IntakeDocument): string | null {
    if (item.status === 'uploaded') {
      return 'Parse';
    }
    if (item.status === 'parsed') {
      return 'Approve';
    }
    if (item.status === 'approved') {
      return 'Promote';
    }
    return null;
  }

  runSourceAction(item: IntakeDocument): void {
    const action = this.sourceActionLabel(item);
    if (!action) {
      return;
    }
    this.sourceActionInFlight.set(item.documentId);
    this.uploadMessage.set(null);
    this.apiError.set(null);

    const request =
      item.status === 'uploaded'
        ? this.api.parseIntakeDocument(item.documentId)
        : item.status === 'parsed'
          ? this.api.approveIntakeDocument(item.documentId)
          : this.api.promoteIntakeDocument(item.documentId);

    request.subscribe({
      next: () => {
        this.uploadMessage.set(`${action} completed for ${item.title}.`);
        this.sourceActionInFlight.set(null);
        if (action === 'Promote' && this.selectedMetadataDocument()?.documentId === item.documentId) {
          this.closeMetadataEditor();
        }
        this.loadMemory();
      },
      error: (error: unknown) => {
        this.apiError.set(error instanceof Error ? error.message : `${action} failed.`);
        this.sourceActionInFlight.set(null);
      },
    });
  }

  private sourceInMemory(item: IntakeDocument): boolean {
    return item.status === 'promoted';
  }

  private refreshMemoryConflicts(teamId: string, scanId: string): void {
    this.api
      .getMemoryConflicts(teamId, scanId)
      .pipe(catchError(() => of(null)))
      .subscribe((conflicts) => {
        this.memoryConflicts.set(conflicts);
      });
  }

  private refreshMemoryReviewState(teamId: string, scanId: string): void {
    forkJoin({
      conflicts: this.api.getMemoryConflicts(teamId, scanId).pipe(catchError(() => of(null))),
      ledger: this.api.getMemoryLedger(teamId).pipe(catchError(() => of(null))),
      conflictResolutions: this.api
        .getMemoryConflictResolutions(teamId)
        .pipe(catchError(() => of(null))),
    }).subscribe(({ conflicts, ledger, conflictResolutions }) => {
      this.memoryConflicts.set(conflicts);
      this.memoryLedger.set(ledger);
      this.memoryConflictResolutions.set(conflictResolutions);
    });
  }

  private claimRow(
    claim: MemoryClaim,
    changeType: ClaimChangeType,
    latestReview?: MemoryReviewEvent,
  ): MemoryClaimReviewRow {
    return {
      claim,
      changeType,
      latestReview,
      effectiveStatus: latestReview?.newStatus ?? claim.governanceStatus,
    };
  }

  private initialTab(): MemoryTab {
    const requested = this.route.snapshot.queryParamMap.get('tab');
    return requested === 'claims' || requested === 'codebase' ? requested : 'sources';
  }

}

function splitConcepts(value: string): string[] {
  return value
    .split(',')
    .map((concept) => concept.trim())
    .filter(Boolean);
}

function shortHash(value: string): string {
  const [, digest = value] = value.split(':');
  return `sha256:${digest.slice(0, 12)}`;
}
