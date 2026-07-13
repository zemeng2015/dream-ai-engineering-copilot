// SPDX-License-Identifier: Apache-2.0

import { Component, Input } from '@angular/core';

import { CodebaseIndexFile } from '../../core/dream-api.service';

@Component({
  selector: 'app-index-json-panel',
  standalone: true,
  templateUrl: './index-json-panel.component.html',
  styleUrl: './index-json-panel.component.scss',
})
export class IndexJsonPanelComponent {
  @Input() repoIndexPath = 'No index artifact loaded';
  @Input() selectedFile: CodebaseIndexFile | null = null;
  @Input() selectedFileJson = '{}';
}
