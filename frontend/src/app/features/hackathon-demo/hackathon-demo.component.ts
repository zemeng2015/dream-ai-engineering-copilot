// SPDX-License-Identifier: Apache-2.0

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { DreamApiService, DreamHealth } from '../../core/dream-api.service';
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

interface HealthFact {
  label: string;
  value: string;
}

type LiveHealthState = 'checking' | 'ready' | 'watch' | 'offline';

@Component({
  selector: 'app-hackathon-demo',
  standalone: true,
  imports: [RouterLink, UiIconComponent],
  templateUrl: './hackathon-demo.component.html',
  styleUrl: './hackathon-demo.component.scss',
})
export class HackathonDemoComponent implements OnInit {
  private readonly dream = inject(DreamApiService);
  private readonly health = signal<DreamHealth | null>(null);

  readonly liveHealthState = signal<LiveHealthState>('checking');
  readonly liveHealthTitle = computed(() => {
    switch (this.liveHealthState()) {
      case 'ready':
        return 'Live Qwen proof ready';
      case 'watch':
        return 'Backend online; Qwen proof needs attention';
      case 'offline':
        return 'Backend offline';
      default:
        return 'Checking backend';
    }
  });
  readonly liveHealthDescription = computed(() => {
    const health = this.health();
    if (health) {
      return `${health.service} returned ${health.status}; no secrets are exposed in this payload.`;
    }
    if (this.liveHealthState() === 'offline') {
      return 'Start the DREAM API on port 8000 in Qwen mode to turn this into live proof.';
    }
    return 'Reading http://127.0.0.1:8000/health for provider, model, deployment target, and proof file.';
  });
  readonly liveHealthFacts = computed<HealthFact[]>(() => {
    const health = this.health();
    if (!health) {
      return [
        { label: 'Endpoint', value: 'http://127.0.0.1:8000/health' },
        {
          label: 'State',
          value: this.liveHealthState() === 'offline' ? 'waiting for backend' : 'checking',
        },
      ];
    }
    return [
      { label: 'Track', value: health.track },
      { label: 'Provider', value: health.llmProvider },
      { label: 'Model', value: health.llmModel ?? 'not reported' },
      { label: 'Deployment', value: health.deploymentTarget },
      { label: 'Alibaba region', value: health.alibabaCloudRegion ?? 'not set' },
      { label: 'API key configured', value: health.llmApiKeyConfigured ? 'yes' : 'no' },
      { label: 'Proof file', value: health.proofFile },
    ];
  });

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

  ngOnInit(): void {
    this.dream
      .getHealth()
      .pipe(
        catchError(() => {
          this.health.set(null);
          this.liveHealthState.set('offline');
          return of(null);
        }),
      )
      .subscribe((health) => {
        if (!health) {
          return;
        }
        this.health.set(health);
        this.liveHealthState.set(this.isReadyHealth(health) ? 'ready' : 'watch');
      });
  }

  private isReadyHealth(health: DreamHealth): boolean {
    return (
      health.status === 'ok' &&
      health.track === 'Track 1: MemoryAgent' &&
      health.llmProvider === 'qwen-cloud' &&
      health.llmApiKeyConfigured &&
      health.proofFile === 'deploy/alibaba/serverless-devs.yaml'
    );
  }
}
