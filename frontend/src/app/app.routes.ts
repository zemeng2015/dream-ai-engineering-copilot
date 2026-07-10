// SPDX-License-Identifier: Apache-2.0

import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'leadership-demo',
    loadComponent: () =>
      import('./features/leadership-demo/leadership-demo.component').then(
        (module) => module.LeadershipDemoComponent,
      ),
    title: 'DREAM Leadership Demo',
  },
  {
    path: 'mission-control',
    loadComponent: () => import('./features/dashboard/dashboard.component').then((module) => module.DashboardComponent),
    title: 'DREAM Mission Control',
  },
  {
    path: 'memory/:documentId',
    loadComponent: () =>
      import('./features/memory-document-detail/memory-document-detail.component').then(
        (module) => module.MemoryDocumentDetailComponent,
      ),
    title: 'DREAM Memory Source Detail',
  },
  {
    path: 'memory',
    loadComponent: () => import('./features/memory-hub/memory-hub.component').then((module) => module.MemoryHubComponent),
    title: 'DREAM Memory Hub',
  },
  {
    path: 'hackathon-demo',
    loadComponent: () =>
      import('./features/hackathon-demo/hackathon-demo.component').then((module) => module.HackathonDemoComponent),
    title: 'DREAM Hackathon Demo',
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
    path: 'context/:caseId',
    loadComponent: () => import('./features/context-detail/context-detail.component').then((module) => module.ContextDetailComponent),
    title: 'DREAM Context Trail',
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
  { path: '', pathMatch: 'full', redirectTo: 'hackathon-demo' },
  { path: '**', redirectTo: 'hackathon-demo' },
];
