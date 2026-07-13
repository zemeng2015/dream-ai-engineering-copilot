// SPDX-License-Identifier: Apache-2.0

import {
  AfterViewChecked,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  inject,
} from '@angular/core';

import { CodebaseIndexFile } from '../../core/dream-api.service';
import { UiIconComponent } from '../../shared/ui-icon.component';

interface RepoTreeFolderRow {
  type: 'folder';
  name: string;
  path: string;
  depth: number;
  fileCount: number;
}

interface RepoTreeFileRow {
  type: 'file';
  name: string;
  path: string;
  depth: number;
  file: CodebaseIndexFile;
}

type RepoTreeRow = RepoTreeFolderRow | RepoTreeFileRow;

@Component({
  selector: 'app-repo-browser-panel',
  standalone: true,
  imports: [UiIconComponent],
  templateUrl: './repo-browser-panel.component.html',
  styleUrl: './repo-browser-panel.component.scss',
})
export class RepoBrowserPanelComponent implements OnChanges, AfterViewChecked {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  @Input() repoName = 'repository';
  @Input() repoPath = '';
  @Input() files: CodebaseIndexFile[] = [];
  @Input() selectedFilePath: string | null = null;

  @Output() readonly fileSelected = new EventEmitter<CodebaseIndexFile>();

  readonly expandedFolders = new Set<string>(['']);
  treeRows: RepoTreeRow[] = [];

  private folderChildren = new Map<string, RepoTreeFolderRow[]>();
  private fileChildren = new Map<string, RepoTreeFileRow[]>();
  private revealSelectedFile = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['files']) {
      this.buildTreeIndex();
    }
    if (changes['selectedFilePath'] && this.selectedFilePath) {
      this.expandAncestors(this.selectedFilePath);
      this.revealSelectedFile = true;
    }
    this.refreshVisibleRows();
  }

  ngAfterViewChecked(): void {
    if (!this.revealSelectedFile) return;
    this.revealSelectedFile = false;
    this.host.nativeElement
      .querySelector<HTMLElement>('.file-row.active')
      ?.scrollIntoView({ block: 'center' });
  }

  toggleFolder(path: string): void {
    if (this.expandedFolders.has(path)) {
      this.expandedFolders.delete(path);
    } else {
      this.expandedFolders.add(path);
    }
    this.refreshVisibleRows();
  }

  isExpanded(path: string): boolean {
    return this.expandedFolders.has(path);
  }

  private buildTreeIndex(): void {
    this.folderChildren = new Map<string, RepoTreeFolderRow[]>();
    this.fileChildren = new Map<string, RepoTreeFileRow[]>();
    const folderPaths = new Set<string>();

    for (const file of this.files) {
      const parts = file.path.split('/').filter(Boolean);
      for (let index = 0; index < parts.length - 1; index += 1) {
        folderPaths.add(parts.slice(0, index + 1).join('/'));
      }
    }

    for (const path of folderPaths) {
      const parts = path.split('/');
      const name = parts.at(-1) ?? path;
      const parent = parts.slice(0, -1).join('/');
      const folders = this.folderChildren.get(parent) ?? [];
      folders.push({
        type: 'folder',
        name,
        path,
        depth: 0,
        fileCount: this.files.filter((file) => file.path.startsWith(`${path}/`)).length,
      });
      this.folderChildren.set(parent, folders);
    }

    for (const file of this.files) {
      const parts = file.path.split('/').filter(Boolean);
      const parent = parts.slice(0, -1).join('/');
      const files = this.fileChildren.get(parent) ?? [];
      files.push({
        type: 'file',
        name: parts.at(-1) ?? file.path,
        path: file.path,
        depth: 0,
        file,
      });
      this.fileChildren.set(parent, files);
    }

    for (const folders of this.folderChildren.values()) {
      folders.sort((left, right) => left.name.localeCompare(right.name));
    }
    for (const files of this.fileChildren.values()) {
      files.sort((left, right) => left.name.localeCompare(right.name));
    }
  }

  private expandAncestors(filePath: string): void {
    const parts = filePath.split('/').filter(Boolean);
    this.expandedFolders.add('');
    for (let index = 0; index < parts.length - 1; index += 1) {
      this.expandedFolders.add(parts.slice(0, index + 1).join('/'));
    }
  }

  private refreshVisibleRows(): void {
    const rows: RepoTreeRow[] = [];
    if (this.expandedFolders.has('')) {
      this.appendChildren('', 1, rows);
    }
    this.treeRows = rows;
  }

  private appendChildren(parent: string, depth: number, rows: RepoTreeRow[]): void {
    for (const folder of this.folderChildren.get(parent) ?? []) {
      rows.push({ ...folder, depth });
      if (this.expandedFolders.has(folder.path)) {
        this.appendChildren(folder.path, depth + 1, rows);
      }
    }
    for (const file of this.fileChildren.get(parent) ?? []) {
      rows.push({ ...file, depth });
    }
  }
}
