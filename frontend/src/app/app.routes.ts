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
    path: 'trust',
    loadComponent: () => import('./features/trust-center/trust-center.component').then((module) => module.TrustCenterComponent),
    title: 'DREAM Trust Center',
  },
  { path: 'dashboard', redirectTo: 'mission-control', pathMatch: 'full' },
  {
    path: 'knowledge',
    loadComponent: () => import('./features/knowledge-base/knowledge-base.component').then((module) => module.KnowledgeBaseComponent),
    title: 'Knowledge Base',
  },
  {
    path: 'knowledge-intake',
    loadComponent: () =>
      import('./features/knowledge-intake/knowledge-intake.component').then((module) => module.KnowledgeIntakeComponent),
    title: 'Knowledge Intake',
  },
  {
    path: 'codebase',
    loadComponent: () =>
      import('./features/codebase-memory/codebase-memory.component').then((module) => module.CodebaseMemoryComponent),
    title: 'Code Index',
  },
  {
    path: 'graph',
    loadComponent: () => import('./features/evidence-graph/evidence-graph.component').then((module) => module.EvidenceGraphComponent),
    title: 'Retrieval Paths',
  },
  {
    path: 'context-intelligence',
    loadComponent: () =>
      import('./features/context-intelligence/context-intelligence.component').then((module) => module.ContextIntelligenceComponent),
    title: 'Context Intelligence',
  },
  {
    path: 'requirements',
    loadComponent: () =>
      import('./features/requirement-draft/requirement-draft.component').then((module) => module.RequirementDraftComponent),
    title: 'Requirement Case',
  },
  {
    path: 'review',
    loadComponent: () => import('./features/pr-review/pr-review.component').then((module) => module.PrReviewComponent),
    title: 'PR Review',
  },
  {
    path: 'testgen',
    loadComponent: () => import('./features/testgen-stub/testgen-stub.component').then((module) => module.TestgenStubComponent),
    title: 'TestGen Stub',
  },
  {
    path: 'audit',
    loadComponent: () => import('./features/audit-eval/audit-eval.component').then((module) => module.AuditEvalComponent),
    title: 'Audit & Eval',
  },
  {
    path: 'settings',
    loadComponent: () => import('./features/settings/settings.component').then((module) => module.SettingsComponent),
    title: 'Settings',
  },
  { path: '', pathMatch: 'full', redirectTo: 'mission-control' },
  { path: '**', redirectTo: 'mission-control' },
];
