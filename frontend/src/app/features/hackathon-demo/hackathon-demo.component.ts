// SPDX-License-Identifier: Apache-2.0

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { DreamApiService, DreamHealth, QwenCloudShowcase } from '../../core/dream-api.service';
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

interface ScorecardItem {
  criterion: string;
  weight: string;
  state: string;
  proof: string;
  tone: 'ready' | 'watch' | 'blocked';
}

interface SubmitGate {
  label: string;
  value: string;
  detail: string;
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
  private readonly showcase = signal<QwenCloudShowcase | null>(null);

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

  readonly scorecardCurrentEvidence = computed(() => {
    const scorecard = this.showcase()?.scorecard;
    return `${scorecard?.weightedCurrentEvidenceReady ?? 55}/${scorecard?.weightedTotal ?? 100}`;
  });
  readonly externalEvidenceGap = computed(() => {
    const scorecard = this.showcase()?.scorecard;
    const total = scorecard?.weightedTotal ?? 100;
    const current = scorecard?.weightedCurrentEvidenceReady ?? 55;
    return `${Math.max(0, total - current)} pts`;
  });
  readonly scorecardDetail = computed(() => {
    const missing = this.showcase()?.scorecard.missingExternalInputs ?? [
      'deployed_backend_url',
      'public_demo_video_url',
    ];
    return missing.length > 0
      ? `Waiting on ${missing.join(', ')}.`
      : 'All judge-facing scorecard inputs are present.';
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

  readonly scorecardItems: ScorecardItem[] = [
    {
      criterion: 'Innovation and AI Creativity',
      weight: '30%',
      state: 'Evidence ready',
      proof: 'Memory distillation, retrieval trails, source-backed generation, and Qwen Cloud provider are in repo and CI.',
      tone: 'ready',
    },
    {
      criterion: 'Problem Value and Impact',
      weight: '25%',
      state: 'Evidence ready',
      proof: 'DREAM targets engineering context loss across tickets, incidents, code, and review history.',
      tone: 'ready',
    },
    {
      criterion: 'Technical Depth and Engineering',
      weight: '30%',
      state: 'Needs live proof',
      proof: 'Docker, CI, API, and Alibaba template are ready; live Function Compute URL closes the final evidence gap.',
      tone: 'watch',
    },
    {
      criterion: 'Presentation and Documentation',
      weight: '15%',
      state: 'Needs public video',
      proof: 'Script, captions, thumbnail, and local MP4 are ready; public video URL closes Devpost presentation proof.',
      tone: 'blocked',
    },
  ];

  readonly submitGates = computed<SubmitGate[]>(() => [
    {
      label: 'Local CI proof',
      value: 'green',
      detail: 'Python tests, lint, PowerShell proof runner, and Bash proof runner pass in GitHub Actions.',
      tone: 'ready',
    },
    {
      label: 'Judge scorecard',
      value: this.scorecardCurrentEvidence(),
      detail: this.scorecardDetail(),
      tone: this.showcase()?.runtime.liveBackendReady ? 'ready' : 'watch',
    },
    {
      label: 'Live inputs',
      value: this.showcase()?.runtime.liveBackendReady ? 'backend live' : 'pending',
      detail: 'Needs env file, public demo URL, Alibaba backend URL, screenshot, and proof recording.',
      tone: this.showcase()?.runtime.liveBackendReady ? 'watch' : 'blocked',
    },
    {
      label: 'Upload bundle',
      value: 'draft',
      detail: 'Bundle exists with hashes; final state waits for external proof assets.',
      tone: 'blocked',
    },
  ]);

  readonly quickProofCommands = [
    'bash scripts/qwencloud-run-local-proof.sh --skip-draft',
    'scripts/qwencloud-run-local-proof.ps1 -SkipDraft',
    'python scripts/qwencloud_seed_demo_artifact.py --promote-count 6',
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

    this.dream
      .getQwenCloudShowcase()
      .pipe(
        catchError(() => {
          this.showcase.set(null);
          return of(null);
        }),
      )
      .subscribe((showcase) => {
        if (showcase) {
          this.showcase.set(showcase);
        }
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
