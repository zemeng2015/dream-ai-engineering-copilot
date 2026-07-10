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
      return 'The guided product flow remains available while the live runtime reconnects.';
    }
    return 'Reading the same-origin /health endpoint for provider, model, deployment target, and proof file.';
  });
  readonly liveHealthFacts = computed<HealthFact[]>(() => {
    const health = this.health();
    if (!health) {
      return [
        { label: 'Endpoint', value: '/health' },
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

  readonly benchmarkFacts = computed<HealthFact[]>(() => {
    const benchmark = this.showcase()?.benchmark;
    if (!benchmark || benchmark.status !== 'ready') {
      return [{ label: 'State', value: 'benchmark evidence loading' }];
    }
    return [
      {
        label: 'Reference score',
        value: `${benchmark.baselineScore.toFixed(1)} to ${benchmark.dreamScore.toFixed(1)}`,
      },
      { label: 'Mean lift', value: `+${benchmark.scoreDelta.toFixed(1)}` },
      { label: 'Paired wins', value: `${benchmark.dreamWins}/${benchmark.caseCount}` },
      {
        label: 'Permutation p',
        value: benchmark.exactPairedPermutationP?.toFixed(4) ?? 'not reported',
      },
      {
        label: 'Exact Recall@12',
        value: `${(benchmark.exactRetrievalRecallAt12 * 100).toFixed(1)}%`,
      },
      { label: 'Qwen model', value: benchmark.model ?? 'not reported' },
    ];
  });
  readonly benchmarkCaveat = computed(() => {
    const benchmark = this.showcase()?.benchmark;
    if (!benchmark || benchmark.status !== 'ready') {
      return 'Loading the reproducible benchmark summary.';
    }
    return (
      `${benchmark.caseCount} synthetic engineering cases, one deterministic completion per arm. ` +
      'Exact retrieval recall is shown because retrieval remains the main measured bottleneck.'
    );
  });

  readonly runtimeSignals = computed<DemoSignal[]>(() => {
    const health = this.health();
    const qwenReady = Boolean(
      health?.llmProvider === 'qwen-cloud' && health.llmApiKeyConfigured,
    );
    const alibabaReady = Boolean(
      health?.deploymentTarget.toLowerCase().includes('alibaba cloud function compute'),
    );
    return [
      {
        label: 'Track',
        value: health?.track ?? 'Track 1: MemoryAgent',
        detail: 'Persistent, source-backed engineering memory.',
        tone: 'ready',
      },
      {
        label: 'Qwen runtime',
        value: health?.llmProvider ?? 'connecting',
        detail: health?.llmModel
          ? `${health.llmModel} with server-side credentials.`
          : 'Waiting for live model metadata.',
        tone: qwenReady ? 'ready' : 'watch',
      },
      {
        label: 'Cloud runtime',
        value: health?.alibabaCloudService ?? 'Alibaba FC',
        detail: health?.alibabaCloudRegion
          ? `Function Compute in ${health.alibabaCloudRegion}.`
          : 'ACR-free custom runtime package.',
        tone: alibabaReady ? 'ready' : 'watch',
      },
      {
        label: 'Evidence mode',
        value: 'Live + traceable',
        detail: health?.proofFile ?? 'Provider and deployment proof loading.',
        tone: this.liveHealthState() === 'ready' ? 'ready' : 'watch',
      },
    ];
  });

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

  readonly submissionEvidence = computed<EvidenceItem[]>(() => {
    const health = this.health();
    const qwenReady = Boolean(
      health?.llmProvider === 'qwen-cloud' && health.llmApiKeyConfigured,
    );
    const runtimeReady = this.showcase()?.runtime.liveBackendReady ?? this.isReadyHealth(health);
    return [
      {
        name: 'Qwen Cloud execution',
        state: qwenReady ? 'Live' : 'Connecting',
        proof: qwenReady
          ? `${health?.llmModel ?? 'Qwen'} is selected by explicit qwen-cloud requests.`
          : 'Live provider metadata is loading from the backend.',
        tone: qwenReady ? 'ready' : 'watch',
      },
      {
        name: 'Alibaba Function Compute',
        state: runtimeReady ? 'Live' : 'Connecting',
        proof: runtimeReady
          ? `${health?.deploymentTarget} in ${health?.alibabaCloudRegion ?? 'the configured region'}.`
          : 'The custom runtime health signal is reconnecting.',
        tone: runtimeReady ? 'ready' : 'watch',
      },
      {
        name: 'Source provenance',
        state: 'Traceable',
        proof: 'Every generated case preserves selected sources, context sections, and prompt preview.',
        tone: 'ready',
      },
      {
        name: 'Human-governed memory',
        state: 'Reviewable',
        proof: 'Promotion, conflicts, waivers, and ratings stay visible in the memory ledger.',
        tone: 'ready',
      },
      {
        name: 'Open reproducibility',
        state: 'Verified',
        proof: 'Apache-2.0 source, cross-platform proof runners, tests, and deployment templates.',
        tone: 'ready',
      },
      {
        name: 'Paired Qwen benchmark',
        state: this.showcase()?.benchmark.status === 'ready' ? 'Measured' : 'Loading',
        proof:
          this.showcase()?.benchmark.status === 'ready'
            ? 'Qwen + DREAM improved all 7 paired synthetic cases with exact-path retrieval disclosed.'
            : 'The benchmark summary is loading from the live showcase endpoint.',
        tone: this.showcase()?.benchmark.status === 'ready' ? 'ready' : 'watch',
      },
    ];
  });

  readonly scorecardItems = computed<ScorecardItem[]>(() => [
    {
      criterion: 'Innovation and AI Creativity',
      weight: '30%',
      state: 'Evidence ready',
      proof: 'Memory distillation, retrieval trails, source-backed generation, and a paired Qwen benchmark are in repo and CI.',
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
      state: this.liveHealthState() === 'ready' ? 'Live proof ready' : 'Runtime connecting',
      proof: 'Angular and FastAPI share one FC endpoint with explicit Qwen calls, CI, tests, and deployment evidence.',
      tone: this.liveHealthState() === 'ready' ? 'ready' : 'watch',
    },
    {
      criterion: 'Presentation and Documentation',
      weight: '15%',
      state: 'Judge flow ready',
      proof: 'This route gives judges a focused five-step walkthrough with runtime and evidence signals.',
      tone: 'ready',
    },
  ]);

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

  private isReadyHealth(health: DreamHealth | null): boolean {
    return (
      health !== null &&
      health.status === 'ok' &&
      health.track === 'Track 1: MemoryAgent' &&
      health.llmProvider === 'qwen-cloud' &&
      health.llmApiKeyConfigured &&
      health.proofFile === 'deploy/alibaba/serverless-devs-runtime.yaml'
    );
  }
}
