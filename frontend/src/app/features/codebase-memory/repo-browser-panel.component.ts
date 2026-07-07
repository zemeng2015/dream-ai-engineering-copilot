// SPDX-License-Identifier: Apache-2.0

import { Component, EventEmitter, Input, Output } from '@angular/core';

import { CodebaseIndexFile } from '../../core/dream-api.service';
import { UiIconComponent } from '../../shared/ui-icon.component';
import { RepoBreadcrumb, RepoFolderEntry } from './codebase-memory.types';

@Component({
  selector: 'app-repo-browser-panel',
  standalone: true,
  imports: [UiIconComponent],
  templateUrl: './repo-browser-panel.component.html',
  styleUrl: './repo-browser-panel.component.scss',
})
export class RepoBrowserPanelComponent {
  @Input() repoPath = '';
  @Input() breadcrumbs: RepoBreadcrumb[] = [];
  @Input() folders: RepoFolderEntry[] = [];
  @Input() files: CodebaseIndexFile[] = [];
  @Input() selectedFilePath: string | null = null;
  @Input() currentFolderPath = '';

  @Output() readonly folderSelected = new EventEmitter<string>();
  @Output() readonly fileSelected = new EventEmitter<CodebaseIndexFile>();

  fileName(path: string): string {
    return path.split('/').pop() || path;
  }

  roleClass(role: string): string {
    if (role === 'test') return 'status-success';
    if (role === 'config') return 'status-warning';
    if (role === 'docs') return 'status-neutral';
    return 'status-info';
  }
}
