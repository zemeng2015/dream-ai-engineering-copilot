// SPDX-License-Identifier: Apache-2.0

import { Routes } from '@angular/router';

import { AuditEvalComponent } from './features/audit-eval/audit-eval.component';
import { CodebaseMemoryComponent } from './features/codebase-memory/codebase-memory.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { EvidenceGraphComponent } from './features/evidence-graph/evidence-graph.component';
import { KnowledgeBaseComponent } from './features/knowledge-base/knowledge-base.component';
import { PrReviewComponent } from './features/pr-review/pr-review.component';
import { RequirementDraftComponent } from './features/requirement-draft/requirement-draft.component';
import { SettingsComponent } from './features/settings/settings.component';
import { TestgenStubComponent } from './features/testgen-stub/testgen-stub.component';

export const routes: Routes = [
  { path: 'dashboard', component: DashboardComponent, title: 'DREAM Dashboard' },
  { path: 'knowledge', component: KnowledgeBaseComponent, title: 'Knowledge Base' },
  { path: 'codebase', component: CodebaseMemoryComponent, title: 'Codebase Memory' },
  { path: 'graph', component: EvidenceGraphComponent, title: 'Evidence Graph' },
  { path: 'requirements', component: RequirementDraftComponent, title: 'Requirement Case' },
  { path: 'review', component: PrReviewComponent, title: 'PR Review' },
  { path: 'testgen', component: TestgenStubComponent, title: 'TestGen Stub' },
  { path: 'audit', component: AuditEvalComponent, title: 'Audit & Eval' },
  { path: 'settings', component: SettingsComponent, title: 'Settings' },
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  { path: '**', redirectTo: 'dashboard' },
];
