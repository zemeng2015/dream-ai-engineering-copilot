// SPDX-License-Identifier: Apache-2.0

import { Component, signal } from '@angular/core';
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
  readonly sidebarCollapsed = signal(false);

  readonly navItems: NavItem[] = [
    { label: 'Mission Control', path: '/mission-control', icon: 'dashboard' },
    { label: 'Engineering Loop', path: '/engineering-loop', icon: 'spark' },
    { label: 'Hackathon Demo', path: '/hackathon-demo', icon: 'spark' },
    { label: 'Memory Hub', path: '/memory', icon: 'database' },
    { label: 'Engineering Workbench', path: '/workbench', icon: 'code' },
    { label: 'Codebase Index', path: '/codebase', icon: 'branch' },
    { label: 'Audit & Eval', path: '/audit', icon: 'shield' },
  ];

  toggleSidebar(): void {
    this.sidebarCollapsed.update((collapsed) => !collapsed);
  }
}
