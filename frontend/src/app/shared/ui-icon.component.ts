// SPDX-License-Identifier: Apache-2.0

import { Component, input } from '@angular/core';

export type UiIconName =
  | 'branch'
  | 'chevron-down'
  | 'chevron-left'
  | 'chevron-right'
  | 'chevron-up'
  | 'clipboard'
  | 'code'
  | 'dashboard'
  | 'database'
  | 'document'
  | 'menu'
  | 'search'
  | 'settings'
  | 'shield'
  | 'spark'
  | 'timeline';

@Component({
  selector: 'app-ui-icon',
  standalone: true,
  template: `
    <svg
      class="ui-icon"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path [attr.d]="path()" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  `,
  styles: [
    `
      .ui-icon {
        display: block;
        width: 21px;
        height: 21px;
      }
    `,
  ],
})
export class UiIconComponent {
  readonly name = input.required<UiIconName>();

  path(): string {
    return ICON_PATHS[this.name()];
  }
}

const ICON_PATHS: Record<UiIconName, string> = {
  branch:
    'M6 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4Zm0 4v4a4 4 0 0 0 4 4h4m4-2a2 2 0 1 1 0 4 2 2 0 0 1 0-4Zm0-8a2 2 0 1 1 0 4 2 2 0 0 1 0-4Zm0 4v2a4 4 0 0 1-4 4h-4',
  'chevron-down': 'M6 9l6 6 6-6',
  'chevron-left': 'M15 6l-6 6 6 6',
  'chevron-right': 'M9 6l6 6-6 6',
  'chevron-up': 'M6 15l6-6 6 6',
  clipboard:
    'M9 5h6m-6 0a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2m-6 0H6.8A1.8 1.8 0 0 0 5 6.8v12.4A1.8 1.8 0 0 0 6.8 21h10.4a1.8 1.8 0 0 0 1.8-1.8V6.8A1.8 1.8 0 0 0 17.2 5H15m-7 7 2.5 2.5L16 9',
  code: 'M8.5 7 4 12l4.5 5M15.5 7 20 12l-4.5 5',
  dashboard:
    'M4 5.8A1.8 1.8 0 0 1 5.8 4h4.4A1.8 1.8 0 0 1 12 5.8v4.4a1.8 1.8 0 0 1-1.8 1.8H5.8A1.8 1.8 0 0 1 4 10.2V5.8Zm8 8A1.8 1.8 0 0 1 13.8 12h4.4a1.8 1.8 0 0 1 1.8 1.8v4.4a1.8 1.8 0 0 1-1.8 1.8h-4.4a1.8 1.8 0 0 1-1.8-1.8v-4.4ZM4 15h5m-5 4h5m7-15v5m-2.5-2.5h5',
  database:
    'M5 7c0-1.7 3.1-3 7-3s7 1.3 7 3-3.1 3-7 3-7-1.3-7-3Zm0 0v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5',
  document: 'M7 3h7l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm7 0v5h5M8.5 12h7M8.5 16h7',
  menu: 'M4 7h16M4 12h16M4 17h16',
  search: 'M10.5 18a7.5 7.5 0 1 1 5.3-2.2L21 21l-2.8-2.8',
  settings:
    'M12 8.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7Zm0-5v2m0 13v2m8.5-8.5h-2m-13 0h-2m14.5-6.5-1.4 1.4M6.9 17.1l-1.4 1.4m0-13 1.4 1.4m10.2 10.2 1.4 1.4',
  shield: 'M12 3 5 6v5.5c0 4.2 2.9 7.9 7 9.5 4.1-1.6 7-5.3 7-9.5V6l-7-3Zm-3 9 2 2 4-5',
  spark: 'M12 3v5m0 8v5M3 12h5m8 0h5m-3.5-6.5-3.2 3.2M9.7 14.3l-3.2 3.2m0-12 3.2 3.2m4.6 5.6 3.2 3.2',
  timeline: 'M5 5v14m0-11h6m-6 5h10m-10 5h14m-8-12 2 2-2 2m4 1 2 2-2 2m4 1 2 2-2 2',
};
