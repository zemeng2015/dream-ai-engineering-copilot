// SPDX-License-Identifier: Apache-2.0

import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MockDreamService } from '../../core/mock-dream.service';
import { UiIconComponent, UiIconName } from '../../shared/ui-icon.component';

interface QuickAction {
  title: string;
  description: string;
  route: string;
  icon: UiIconName;
}

interface PipelineStep {
  label: string;
  value: string;
  description: string;
  status: 'ready' | 'review' | 'local';
  route: string;
}

interface Guardrail {
  label: string;
  value: string;
  status: 'success' | 'warning' | 'info';
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, UiIconComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  private readonly dream = inject(MockDreamService);

  readonly runs = this.dream.recentRuns;
  readonly packs = this.dream.listKnowledgePacks();
  readonly ratings = this.dream.ratings;
  readonly cases = this.dream.requirementCases;
  readonly scorecards = this.dream.scorecards;
  readonly codeFiles = this.dream.listCodebaseFiles();
  readonly graphPaths = this.dream.searchEvidenceGraph({ query: 'execution status', topK: 3 });
  readonly primaryCase = computed(() => this.cases()[0]);
  readonly needsReview = computed(() =>
    this.dream.auditRuns().filter((run) => run.status === 'needs_review' || run.status === 'warning'),
  );
  readonly missionMetrics = computed(() => [
    { label: 'Memory Sources', value: this.dream.listKnowledgeChunks().length + this.codeFiles.length, note: 'docs + code' },
    { label: 'Requirement Cases', value: this.cases().length, note: 'brief ready' },
    { label: 'Eval Scorecards', value: this.scorecards().length, note: 'rule-based' },
    { label: 'Human Ratings', value: this.ratings().length, note: 'stored locally' },
    { label: 'Needs Review', value: this.needsReview().length, note: 'human gate' },
  ]);
  readonly pipelineSteps = computed<PipelineStep[]>(() => [
    {
      label: 'Knowledge Packs',
      value: `${this.dream.listKnowledgeChunks().length} chunks`,
      description: 'Domain docs, runbooks, incidents, Jira, PR memory.',
      status: 'ready',
      route: '/memory',
    },
    {
      label: 'Codebase Index',
      value: `${this.codeFiles.length} files`,
      description: 'Frontend, backend, AWS, Python, and tests.',
      status: 'ready',
      route: '/memory',
    },
    {
      label: 'Retrieval Paths',
      value: `${this.graphPaths.length} paths`,
      description: 'Concepts linked to code, risks, tests, and history.',
      status: 'local',
      route: '/memory',
    },
    {
      label: 'Review Workflows',
      value: `${this.cases().length} cases`,
      description: 'Requirement Case and PR Review stay draft-only.',
      status: 'review',
      route: '/workbench',
    },
    {
      label: 'Eval & Audit',
      value: `${this.scorecards().length} scorecards`,
      description: 'Rule-based checks plus human ratings.',
      status: 'review',
      route: '/trust',
    },
  ]);
  readonly guardrails: Guardrail[] = [
    { label: 'External mutation', value: 'Disabled', status: 'success' },
    { label: 'Provider default', value: 'Mock local', status: 'info' },
    { label: 'Human approval', value: 'Required', status: 'warning' },
  ];

  readonly quickActions: QuickAction[] = [
    {
      title: 'Requirement Case',
      description: 'Turn rough requests into impact maps, briefs, and Jira drafts.',
      route: '/workbench',
      icon: 'document',
    },
    {
      title: 'Code Index',
      description: 'Search symbols, layers, concepts, and test mappings.',
      route: '/memory',
      icon: 'branch',
    },
    {
      title: 'PR Review',
      description: 'Review fake diffs with source-backed codebase context.',
      route: '/workbench',
      icon: 'code',
    },
    {
      title: 'Memory Hub',
      description: 'Retrieve DFP docs, incidents, Jira, PRs, and concept memory.',
      route: '/memory',
      icon: 'search',
    },
    {
      title: 'Trust Center',
      description: 'Inspect scorecards, evidence coverage, and review gates.',
      route: '/trust',
      icon: 'shield',
    },
    {
      title: 'Context Trail',
      description: 'Review retrieval paths, prompt preview, and logic chain.',
      route: '/trust',
      icon: 'timeline',
    },
  ];
}
