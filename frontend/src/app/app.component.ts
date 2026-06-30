// SPDX-License-Identifier: Apache-2.0

import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { UiIconComponent, UiIconName } from './shared/ui-icon.component';

interface NavItem {
  label: string;
  path: string;
  icon: UiIconName;
}

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet, UiIconComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  readonly navItems: NavItem[] = [
    { label: 'Mission Control', path: '/mission-control', icon: 'dashboard' },
    { label: 'Memory Hub', path: '/memory', icon: 'database' },
    { label: 'Engineering Workbench', path: '/workbench', icon: 'code' },
    { label: 'Trust Center', path: '/trust', icon: 'shield' },
    { label: 'Settings', path: '/settings', icon: 'settings' },
  ];
}
