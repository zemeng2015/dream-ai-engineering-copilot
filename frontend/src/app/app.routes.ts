// SPDX-License-Identifier: Apache-2.0

import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'mission-control',
    loadComponent: () => import('./features/dashboard/dashboard.component').then((module) => module.DashboardComponent),
    title: 'DREAM Mission Control',
  },
  {
    path: 'memory',
    loadComponent: () => import('./features/memory-hub/memory-hub.component').then((module) => module.MemoryHubComponent),
    title: 'DREAM Memory Hub',
  },
  {
    path: 'workbench',
    loadComponent: () =>
      import('./features/engineering-workbench/engineering-workbench.component').then(
        (module) => module.EngineeringWorkbenchComponent,
      ),
    title: 'DREAM Engineering Workbench',
  },
  {
    path: 'requirements',
    loadComponent: () =>
      import('./features/engineering-workbench/engineering-workbench.component').then(
        (module) => module.EngineeringWorkbenchComponent,
      ),
    title: 'DREAM Jira Draft',
    data: { mode: 'requirement' },
  },
  {
    path: 'review',
    loadComponent: () =>
      import('./features/engineering-workbench/engineering-workbench.component').then(
        (module) => module.EngineeringWorkbenchComponent,
      ),
    title: 'DREAM PR Review',
    data: { mode: 'pr' },
  },
  {
    path: 'codebase',
    loadComponent: () =>
      import('./features/codebase-memory/codebase-memory.component').then((module) => module.CodebaseMemoryComponent),
    title: 'DREAM Codebase Index',
  },
  {
    path: 'audit/:targetId',
    loadComponent: () => import('./features/audit-eval/audit-eval.component').then((module) => module.AuditEvalComponent),
    title: 'Audit & Eval Detail',
  },
  {
    path: 'audit',
    loadComponent: () => import('./features/audit-eval/audit-eval.component').then((module) => module.AuditEvalComponent),
    title: 'Audit & Eval',
  },
  { path: 'dashboard', redirectTo: 'mission-control', pathMatch: 'full' },
  { path: 'trust', redirectTo: 'audit', pathMatch: 'full' },
  { path: 'knowledge', redirectTo: 'memory', pathMatch: 'full' },
  { path: 'knowledge-intake', redirectTo: 'memory', pathMatch: 'full' },
  { path: 'graph', redirectTo: 'codebase', pathMatch: 'full' },
  { path: 'context-intelligence', redirectTo: 'audit', pathMatch: 'full' },
  { path: 'testgen', redirectTo: 'workbench', pathMatch: 'full' },
  { path: 'settings', redirectTo: 'mission-control', pathMatch: 'full' },
  { path: '', pathMatch: 'full', redirectTo: 'mission-control' },
  { path: '**', redirectTo: 'mission-control' },
];
