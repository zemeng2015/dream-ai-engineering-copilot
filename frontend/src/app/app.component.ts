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
    { label: 'Mission Control', path: '/dashboard', icon: 'dashboard' },
    { label: 'Knowledge Memory', path: '/knowledge', icon: 'database' },
    { label: 'Knowledge Intake', path: '/knowledge-intake', icon: 'document' },
    { label: 'Codebase Memory', path: '/codebase', icon: 'branch' },
    { label: 'Evidence Graph', path: '/graph', icon: 'timeline' },
    { label: 'Context Intelligence', path: '/context-intelligence', icon: 'spark' },
    { label: 'Requirement Case', path: '/requirements', icon: 'document' },
    { label: 'PR Review', path: '/review', icon: 'code' },
    { label: 'Eval & Audit', path: '/audit', icon: 'shield' },
    { label: 'TestGen Stub', path: '/testgen', icon: 'clipboard' },
    { label: 'Settings', path: '/settings', icon: 'settings' },
  ];
}
