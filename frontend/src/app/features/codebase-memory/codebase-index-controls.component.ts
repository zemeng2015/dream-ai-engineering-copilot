// SPDX-License-Identifier: Apache-2.0

import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';

import { UiIconComponent } from '../../shared/ui-icon.component';

@Component({
  selector: 'app-codebase-index-controls',
  standalone: true,
  imports: [ReactiveFormsModule, UiIconComponent],
  templateUrl: './codebase-index-controls.component.html',
  styleUrl: './codebase-index-controls.component.scss',
})
export class CodebaseIndexControlsComponent {
  @Input({ required: true }) form!: FormGroup;
  @Input() isLoading = false;
  @Input() isIndexing = false;

  @Output() readonly searchRequested = new EventEmitter<void>();
  @Output() readonly indexRequested = new EventEmitter<void>();
}
