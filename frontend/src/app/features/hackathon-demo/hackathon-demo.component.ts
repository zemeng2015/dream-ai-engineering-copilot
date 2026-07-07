// SPDX-License-Identifier: Apache-2.0

import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { UiIconComponent, UiIconName } from '../../shared/ui-icon.component';

interface DemoSignal {
  label: string;
  value: string;
  detail: string;
  tone: 'ready' | 'watch' | 'blocked';
}

interface DemoStep {
  order: string;
  title: string;
  outcome: string;
  route: string;
  routeLabel: string;
  evidence: string;
  icon: UiIconName;
}

interface EvidenceItem {
  name: string;
  state: string;
  proof: string;
  tone: 'ready' | 'watch' | 'blocked';
}

@Component({
  selector: 'app-hackathon-demo',
  standalone: true,
  imports: [RouterLink, UiIconComponent],
  templateUrl: './hackathon-demo.component.html',
  styleUrl: './hackathon-demo.component.scss',
})
export class HackathonDemoComponent {
  readonly runtimeSignals: DemoSignal[] = [
    {
      label: 'Track',
      value: 'Track 1: MemoryAgent',
      detail: 'Persistent source-backed engineering memory.',
      tone: 'ready',
    },
    {
      label: 'Runtime provider',
      value: 'qwen-cloud',
      detail: 'Qwen Cloud through the OpenAI-compatible adapter.',
      tone: 'ready',
    },
    {
      label: 'Deployment proof',
      value: 'Alibaba FC',
      detail: 'Custom container template is in deploy/alibaba/serverless-devs.yaml.',
      tone: 'watch',
    },
    {
      label: 'Final submit',
      value: 'July 9, 2026',
      detail: '2:00pm PDT / 5:00pm EDT Devpost deadline.',
      tone: 'blocked',
    },
  ];

  readonly demoSteps: DemoStep[] = [
    {
      order: '01',
      title: 'Approve source-backed memory',
      outcome: 'Review source claims, conflicts, section proofs, and promoted memory before generation.',
      route: '/memory',
      routeLabel: 'Open Memory Hub',
      evidence: 'Knowledge packs, intake proof, claim review ledger.',
      icon: 'database',
    },
    {
      order: '02',
      title: 'Generate a requirement case',
      outcome: 'Turn a rough engineering request into questions, impact areas, an engineering brief, and Jira draft.',
      route: '/requirements',
      routeLabel: 'Open Workbench',
      evidence: 'Qwen-backed draft flow with source paths and human-review status.',
      icon: 'clipboard',
    },
    {
      order: '03',
      title: 'Inspect the context trail',
      outcome: 'Show the retrieval path before the model writes: query normalization, graph expansion, code binding, and eval.',
      route: '/context/case_async_status',
      routeLabel: 'Open Context Trail',
      evidence: 'Context pack sections, selected evidence, prompt preview, logic chain.',
      icon: 'timeline',
    },
    {
      order: '04',
      title: 'Bind codebase evidence',
      outcome: 'Map the requirement to backend, frontend, test, incident, and historical PR/Jira sources.',
      route: '/codebase',
      routeLabel: 'Open Codebase Index',
      evidence: 'DFP synthetic repo index and cross-source retrieval paths.',
      icon: 'branch',
    },
    {
      order: '05',
      title: 'Close with audit and eval',
      outcome: 'Prove the output is reviewable with scorecards, warnings, ratings, and source coverage.',
      route: '/audit',
      routeLabel: 'Open Audit & Eval',
      evidence: 'Eval agent scorecards, audit runs, and human rating loop.',
      icon: 'shield',
    },
  ];

  readonly submissionEvidence: EvidenceItem[] = [
    {
      name: 'Public repo and license',
      state: 'Ready',
      proof: 'GitHub repo is public and Apache-2.0 checks pass in final readiness.',
      tone: 'ready',
    },
    {
      name: 'Local reproducibility',
      state: 'Ready',
      proof: 'PowerShell and Bash local proof runners are green in CI.',
      tone: 'ready',
    },
    {
      name: 'Demo video render',
      state: 'Ready',
      proof: 'Rendered MP4 is 1280x720 and under three minutes.',
      tone: 'ready',
    },
    {
      name: 'Public video URL',
      state: 'Action required',
      proof: 'Upload to YouTube, Vimeo, or Facebook Video after action-time confirmation.',
      tone: 'blocked',
    },
    {
      name: 'Alibaba deployment proof',
      state: 'Action required',
      proof: 'Needs deployed backend URL, screenshot, and separate proof recording from the live FC endpoint.',
      tone: 'blocked',
    },
  ];

  readonly quickProofCommands = [
    'bash scripts/qwencloud-run-local-proof.sh --skip-draft',
    'scripts/qwencloud-run-local-proof.ps1 -SkipDraft',
    'scripts/qwencloud-final-readiness.ps1 -AllowDraftPacket',
  ];
}
