// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';

import {
  CodebaseIndexFile,
  DreamApiService,
  IntakeDocument,
} from '../../core/dream-api.service';
import { UiIconComponent } from '../../shared/ui-icon.component';

type MemoryTab = 'sources' | 'codebase';

interface MemoryTabItem {
  id: MemoryTab;
  label: string;
  count: number | string;
  note: string;
  status: string;
  tone: 'info' | 'warning' | 'success';
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

  readonly isLoading = signal(false);
  readonly uploadInFlight = signal(false);
  readonly sourceActionInFlight = signal<string | null>(null);
  readonly apiError = signal<string | null>(null);
  readonly uploadMessage = signal<string | null>(null);
  readonly intakeDocuments = signal<IntakeDocument[]>([]);
  readonly codebaseFiles = signal<CodebaseIndexFile[]>([]);
  readonly activeTab = signal<MemoryTab>('sources');

  readonly uploadForm = this.fb.nonNullable.group({
    teamId: ['demo_team', Validators.required],
    filePath: ['examples/intake-samples/runbook-output-reconciliation.md', Validators.required],
    documentType: ['runbooks', Validators.required],
    title: [''],
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

  readonly memoryTabs = computed<MemoryTabItem[]>(() => [
    {
      id: 'sources',
      label: 'Source Intake',
      count: this.intakeDocuments().length,
      note: `${this.sourceReviewQueue().length} need review / ${this.approvedSourceItems().length} promoted`,
      status: this.sourceReviewQueue().length ? 'Review pending' : 'Current',
      tone: this.sourceReviewQueue().length ? 'warning' : 'success',
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
    }).subscribe({
      next: ({ intakeDocuments, codebaseFiles }) => {
        this.intakeDocuments.set(intakeDocuments);
        this.codebaseFiles.set(codebaseFiles);
        this.isLoading.set(false);
      },
      error: () => {
        this.apiError.set('FastAPI memory data could not be loaded.');
        this.isLoading.set(false);
      },
    });
  }

  registerSource(): void {
    if (this.uploadForm.invalid) {
      this.uploadForm.markAllAsTouched();
      return;
    }
    this.uploadInFlight.set(true);
    this.uploadMessage.set(null);
    this.apiError.set(null);
    const value = this.uploadForm.getRawValue();
    this.api
      .uploadIntakeDocument({
        teamId: value.teamId,
        filePath: value.filePath,
        documentType: value.documentType,
        title: value.title.trim() || undefined,
      })
      .subscribe({
        next: (document) => {
          this.intakeDocuments.update((items) => [document, ...items.filter((item) => item.documentId !== document.documentId)]);
          this.uploadMessage.set(`Registered ${document.title}.`);
          this.uploadInFlight.set(false);
        },
        error: (error: unknown) => {
          this.apiError.set(error instanceof Error ? error.message : 'Source registration failed.');
          this.uploadInFlight.set(false);
        },
      });
  }

  sourceReviewSummary(item: IntakeDocument): string {
    return `${item.documentType} / ${this.sourceFileName(item)}`;
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

  setActiveTab(tab: MemoryTab): void {
    this.activeTab.set(tab);
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
}
