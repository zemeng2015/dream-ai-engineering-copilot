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

  readonly quickActions: QuickAction[] = [
    {
      title: 'Requirement Case',
      description: 'Turn rough requests into impact maps, briefs, and Jira drafts.',
      route: '/requirements',
      icon: 'document',
    },
    {
      title: 'Codebase Memory',
      description: 'Search symbols, layers, concepts, and test mappings.',
      route: '/codebase',
      icon: 'branch',
    },
    {
      title: 'PR Review',
      description: 'Review fake diffs with source-backed codebase context.',
      route: '/review',
      icon: 'code',
    },
    {
      title: 'Knowledge Memory',
      description: 'Retrieve DFP docs, incidents, Jira, PRs, and concept memory.',
      route: '/knowledge',
      icon: 'search',
    },
    {
      title: 'Eval Agent',
      description: 'Inspect scorecards, evidence coverage, and review gates.',
      route: '/audit',
      icon: 'shield',
    },
    {
      title: 'TestGen Stub',
      description: 'Validate plugin flow without unit-test generation.',
      route: '/testgen',
      icon: 'clipboard',
    },
  ];
}
