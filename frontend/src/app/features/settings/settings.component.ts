import { Component, inject } from '@angular/core';

import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  templateUrl: './settings.component.html',
})
export class SettingsComponent {
  readonly dream = inject(MockDreamService);
}

