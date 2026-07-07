// SPDX-License-Identifier: Apache-2.0

import { Component, Input } from '@angular/core';

import { CodebaseIndexFile } from '../../core/dream-api.service';

@Component({
  selector: 'app-code-preview-panel',
  standalone: true,
  templateUrl: './code-preview-panel.component.html',
  styleUrl: './code-preview-panel.component.scss',
})
export class CodePreviewPanelComponent {
  @Input() selectedFile: CodebaseIndexFile | null = null;
  @Input() codeLines: string[] = [];
  @Input() isFileLoading = false;

  roleClass(role: string): string {
    if (role === 'test') return 'status-success';
    if (role === 'config') return 'status-warning';
    if (role === 'docs') return 'status-neutral';
    return 'status-info';
  }

  formatBytes(sizeBytes: number): string {
    if (sizeBytes < 1024) return `${sizeBytes} B`;
    return `${Number((sizeBytes / 1024).toFixed(1))} KB`;
  }
}
