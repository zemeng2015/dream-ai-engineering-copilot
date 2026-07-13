// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';

import {
  CodebaseConcept,
  CodebaseFileContent,
  CodebaseIndexArtifact,
  CodebaseIndexFile,
  CodebaseIndexSummary,
  CodebaseSearchItem,
  DreamApiService,
} from '../../core/dream-api.service';
import { CodePreviewPanelComponent } from './code-preview-panel.component';
import { CodebaseIndexControlsComponent } from './codebase-index-controls.component';
import { CodebaseSummaryCardsComponent } from './codebase-summary-cards.component';
import { EvidenceSearchPanelComponent } from './evidence-search-panel.component';
import { ImpactMapPanelComponent } from './impact-map-panel.component';
import { IndexJsonPanelComponent } from './index-json-panel.component';
import { RepoBrowserPanelComponent } from './repo-browser-panel.component';

@Component({
  selector: 'app-codebase-memory',
  standalone: true,
  imports: [
    CodebaseIndexControlsComponent,
    CodebaseSummaryCardsComponent,
    RepoBrowserPanelComponent,
    CodePreviewPanelComponent,
    IndexJsonPanelComponent,
    EvidenceSearchPanelComponent,
    ImpactMapPanelComponent,
  ],
  templateUrl: './codebase-memory.component.html',
  styleUrl: './codebase-memory.component.scss',
})
export class CodebaseMemoryComponent {
  private readonly api = inject(DreamApiService);
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);

  readonly isLoading = signal(false);
  readonly isIndexing = signal(false);
  readonly isFileLoading = signal(false);
  readonly apiError = signal<string | null>(null);
  readonly indexSummary = signal<CodebaseIndexSummary | null>(null);
  readonly indexArtifact = signal<CodebaseIndexArtifact | null>(null);
  readonly files = signal<CodebaseIndexFile[]>([]);
  readonly concepts = signal<CodebaseConcept[]>([]);
  readonly results = signal<CodebaseSearchItem[]>([]);
  readonly selectedFilePath = signal<string | null>(null);
  readonly selectedFileContent = signal<CodebaseFileContent | null>(null);

  readonly form = this.fb.nonNullable.group({
    teamId: ['demo_team', Validators.required],
    repoName: ['dfp-demo-repo', Validators.required],
    repoPath: ['examples/dfp-demo-repo', Validators.required],
    query: ['status tracking output collector tests', Validators.required],
    topK: [8, [Validators.required, Validators.min(1), Validators.max(20)]],
  });

  readonly sourceFileCount = computed(() =>
    this.files().filter((file) => file.role === 'source').length,
  );
  readonly testFileCount = computed(() =>
    this.files().filter((file) => file.role === 'test').length,
  );
  readonly symbolCount = computed(() =>
    this.files().reduce((count, file) => count + file.symbols.length, 0),
  );
  readonly selectedFile = computed(() => {
    const selectedPath = this.selectedFilePath();
    return this.files().find((file) => file.path === selectedPath) ?? this.files()[0] ?? null;
  });
  readonly topConcepts = computed(() =>
    [...this.concepts()].sort((a, b) => b.relatedFiles.length - a.relatedFiles.length).slice(0, 10),
  );
  readonly selectedImpactConcepts = computed(() => {
    const filePath = this.selectedFilePath();
    if (!filePath) return [];
    return this.concepts()
      .filter(
        (concept) =>
          concept.relatedFiles.includes(filePath) ||
          concept.relatedTests.includes(filePath) ||
          concept.relatedDocs.includes(filePath),
      )
      .slice(0, 6);
  });
  readonly codeLines = computed(() => this.selectedFileContent()?.content.split(/\r?\n/) ?? []);
  readonly selectedFileJson = computed(() => {
    const file = this.selectedFile();
    return file ? JSON.stringify(file, null, 2) : '{}';
  });
  readonly repoIndexPath = computed(() => this.indexArtifact()?.indexPath ?? 'No index artifact loaded');

  constructor() {
    this.loadIndex();
  }

  loadIndex(): void {
    const value = this.form.getRawValue();
    this.isLoading.set(true);
    this.apiError.set(null);
    forkJoin({
      artifact: this.api
        .getCodebaseIndex(value.teamId, value.repoName)
        .pipe(catchError(() => of(null as CodebaseIndexArtifact | null))),
      files: this.api
        .listCodebaseFiles(value.teamId, value.repoName)
        .pipe(catchError(() => of([] as CodebaseIndexFile[]))),
      concepts: this.api
        .listCodebaseConcepts(value.teamId, value.repoName)
        .pipe(catchError(() => of([] as CodebaseConcept[]))),
      results: this.api
        .searchCodebaseIndex(value.teamId, value.repoName, value.query, value.topK)
        .pipe(catchError(() => of([] as CodebaseSearchItem[]))),
    }).subscribe({
      next: ({ artifact, files, concepts, results }) => {
        this.indexArtifact.set(artifact);
        this.indexSummary.set(artifact?.summary ?? null);
        this.files.set(files);
        this.concepts.set(concepts);
        this.results.set(results);

        const requestedPath = this.route.snapshot.queryParamMap.get('file');
        const currentPath = this.selectedFilePath();
        const requestedFileExists = requestedPath && files.some((file) => file.path === requestedPath);
        const currentFileExists = currentPath && files.some((file) => file.path === currentPath);
        const nextPath = requestedFileExists ? requestedPath : currentFileExists ? currentPath : files[0]?.path ?? null;
        this.selectedFilePath.set(nextPath);
        if (nextPath) {
          this.loadFileContent(nextPath);
        } else {
          this.selectedFileContent.set(null);
        }

        this.isLoading.set(false);
        if (!files.length) {
          this.apiError.set('No codebase index was loaded. Run Index Repo to create or refresh it.');
        }
      },
      error: () => {
        this.apiError.set('Codebase API data could not be loaded.');
        this.isLoading.set(false);
      },
    });
  }

  refreshIndex(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.isIndexing.set(true);
    this.apiError.set(null);
    this.api.indexCodebase(value.teamId, value.repoPath, value.repoName).subscribe({
      next: (summary) => {
        this.indexSummary.set(summary);
        this.isIndexing.set(false);
        this.loadIndex();
      },
      error: (error: unknown) => {
        this.apiError.set(apiErrorMessage(error, 'Codebase indexing failed.'));
        this.isIndexing.set(false);
      },
    });
  }

  runSearch(): void {
    const value = this.form.getRawValue();
    this.apiError.set(null);
    this.api.searchCodebaseIndex(value.teamId, value.repoName, value.query, value.topK).subscribe({
      next: (results) => this.results.set(results),
      error: (error: unknown) => {
        this.apiError.set(apiErrorMessage(error, 'Codebase search failed.'));
        this.results.set([]);
      },
    });
  }

  selectFile(file: CodebaseIndexFile): void {
    this.selectPath(file.path);
  }

  selectPath(path: string): void {
    if (!this.files().some((file) => file.path === path)) {
      return;
    }
    this.selectedFilePath.set(path);
    this.loadFileContent(path);
  }

  loadFileContent(path: string): void {
    const value = this.form.getRawValue();
    this.isFileLoading.set(true);
    this.api.getCodebaseFileContent(value.teamId, value.repoName, path).subscribe({
      next: (file) => {
        if (this.selectedFilePath() === file.path) {
          this.selectedFileContent.set(file);
        }
        this.isFileLoading.set(false);
      },
      error: (error: unknown) => {
        if (this.selectedFilePath() === path) {
          this.selectedFileContent.set(null);
        }
        this.apiError.set(apiErrorMessage(error, 'File content could not be loaded.'));
        this.isFileLoading.set(false);
      },
    });
  }

}

function apiErrorMessage(error: unknown, fallback: string): string {
  if (isApiError(error)) {
    const detail = error.error?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (typeof error.message === 'string' && error.message.trim()) {
      return error.message;
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

function isApiError(error: unknown): error is {
  error?: { detail?: unknown };
  message?: string;
} {
  return typeof error === 'object' && error !== null;
}
