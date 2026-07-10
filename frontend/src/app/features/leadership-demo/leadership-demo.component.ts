// SPDX-License-Identifier: Apache-2.0

import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { UiIconComponent, UiIconName } from '../../shared/ui-icon.component';

interface TrustSignal {
  label: string;
  value: string;
  detail: string;
  tone: 'trust' | 'control' | 'evidence';
}

interface ComparisonRow {
  dimension: string;
  stateless: string;
  dream: string;
}

interface DemoStep {
  order: string;
  title: string;
  outcome: string;
  proof: string;
  route: string;
  action: string;
  icon: UiIconName;
}

interface PilotBoundary {
  label: string;
  value: string;
}

@Component({
  selector: 'app-leadership-demo',
  standalone: true,
  imports: [RouterLink, UiIconComponent],
  templateUrl: './leadership-demo.component.html',
  styleUrl: './leadership-demo.component.scss',
})
export class LeadershipDemoComponent {
  readonly trustSignals: TrustSignal[] = [
    {
      label: 'Knowledge boundary',
      value: 'Approved sources only',
      detail: 'Candidate, rejected, quarantined, and conflicted claims stay out of generation.',
      tone: 'trust',
    },
    {
      label: 'Decision boundary',
      value: 'Human approval required',
      detail: 'Open questions remain visible and block Jira-ready status until reviewed.',
      tone: 'control',
    },
    {
      label: 'Evidence boundary',
      value: 'Every claim is traceable',
      detail: 'Outputs retain source paths, review identity, context trail, eval, and audit records.',
      tone: 'evidence',
    },
    {
      label: 'Action boundary',
      value: 'No automatic external writes',
      detail: 'The leadership scenario produces reviewable drafts without changing Jira or GitHub.',
      tone: 'control',
    },
  ];

  readonly comparisonRows: ComparisonRow[] = [
    {
      dimension: 'Organizational context',
      stateless: 'Starts from the prompt and general model knowledge.',
      dream: 'Uses approved architecture, runbooks, incidents, tests, and code evidence.',
    },
    {
      dimension: 'Ambiguity handling',
      stateless: 'Often fills gaps with plausible assumptions.',
      dream: 'Creates role-specific questions and preserves unresolved decisions.',
    },
    {
      dimension: 'Impact analysis',
      stateless: 'Suggests generic components and test areas.',
      dream: 'Binds the request to concrete files, historical risks, and test references.',
    },
    {
      dimension: 'Trust and review',
      stateless: 'The reviewer must reconstruct why the answer was produced.',
      dream: 'Shows source proof, selection reasons, governance status, eval, and audit.',
    },
  ];

  readonly demoSteps: DemoStep[] = [
    {
      order: '01',
      title: 'Approve organizational memory',
      outcome: 'Review source-backed claims before they can influence any generated artifact.',
      proof: 'Claim status, conflict gate, reviewer, source span, and ledger event.',
      route: '/memory',
      action: 'Open Memory Hub',
      icon: 'database',
    },
    {
      order: '02',
      title: 'Start from a rough request',
      outcome: 'Use the kind of incomplete business request teams receive every day.',
      proof: 'The raw request remains visible beside the generated context.',
      route: '/requirements',
      action: 'Open Requirement Flow',
      icon: 'clipboard',
    },
    {
      order: '03',
      title: 'Expose impact and uncertainty',
      outcome: 'Identify affected code, tests, operational context, and role-owned questions.',
      proof: 'Jira readiness stays blocked while material questions remain open.',
      route: '/requirements',
      action: 'Review Impact',
      icon: 'code',
    },
    {
      order: '04',
      title: 'Inspect the evidence trail',
      outcome: 'Trace a generated decision back to approved memory and underlying sources.',
      proof: 'Selected evidence, why-selected reasoning, claim governance, and prompt preview.',
      route: '/context/case_async_status',
      action: 'Open Context Trail',
      icon: 'timeline',
    },
    {
      order: '05',
      title: 'Close with eval and audit',
      outcome: 'Review what the draft covered, what it missed, and who rated the result.',
      proof: 'Independent scorecard, warnings, model record, sources, and human rating.',
      route: '/audit',
      action: 'Open Audit & Eval',
      icon: 'shield',
    },
  ];

  readonly pilotBoundaries: PilotBoundary[] = [
    { label: 'Scope', value: 'One team · one application · one repository' },
    { label: 'Duration', value: 'Proposed six-week controlled pilot' },
    { label: 'Sources', value: 'Read-only, explicitly approved engineering content' },
    { label: 'Actions', value: 'Draft generation only; no automatic Jira or PR writes' },
    { label: 'Review', value: 'BA / TL / QA subject-matter approval required' },
    { label: 'Exit', value: 'Stop if trust, usefulness, or data-boundary gates fail' },
  ];
}
