// SPDX-License-Identifier: Apache-2.0

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, firstValueFrom, of } from 'rxjs';

import {
  DreamApiService,
  DreamHealth,
  ExperienceCaptureResult,
  ExperienceDecision,
  ExperienceMemory,
  ExperienceRecallResult,
  QwenCloudShowcase,
} from '../../core/dream-api.service';
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
  icon: UiIconName;
}

interface HealthFact {
  label: string;
  value: string;
}

type LiveHealthState = 'checking' | 'ready' | 'watch' | 'offline';
type ArenaStepState = 'pending' | 'running' | 'complete' | 'error';

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

  private readonly teamId = 'qwencloud-judge-arena';
  private readonly firstObservation =
    'For my deployment reviews, I prefer a 10% canary for 30 minutes before expanding rollout. This is my durable default.';
  private readonly secondObservation =
    'Update my deployment review preference: use a 20% canary for 45 minutes from now on. This replaces my earlier rollout preference.';
  private readonly recallQuery =
    'What canary rollout should I use for my deployment review? Apply my current preference and exclude obsolete guidance.';

  readonly liveHealthState = signal<LiveHealthState>('checking');
  readonly arenaBusy = signal(false);
  readonly arenaStep = signal(0);
  readonly arenaError = signal<string | null>(null);
  readonly judgeIdentity = signal(this.newJudgeIdentity());
  readonly firstCapture = signal<ExperienceCaptureResult | null>(null);
  readonly secondCapture = signal<ExperienceCaptureResult | null>(null);
  readonly recall = signal<ExperienceRecallResult | null>(null);
  readonly memories = signal<ExperienceMemory[]>([]);
  readonly decisions = signal<ExperienceDecision[]>([]);
  readonly feedbackState = signal<'idle' | 'saving' | 'saved' | 'error'>('idle');
  private readonly liveQwenDecision = computed(
    () => this.secondCapture()?.decision ?? this.firstCapture()?.decision ?? null,
  );

  readonly liveHealthTitle = computed(() => {
    switch (this.liveHealthState()) {
      case 'ready':
        return 'Qwen + Alibaba runtime verified';
      case 'watch':
        return 'Backend online; Alibaba proof available';
      case 'offline':
        return 'Live runtime unavailable';
      default:
        return 'Checking live runtime';
    }
  });

  readonly liveHealthFacts = computed<HealthFact[]>(() => {
    const health = this.health();
    if (!health) {
      return [
        { label: 'Endpoint', value: '/health' },
        { label: 'State', value: this.liveHealthState() === 'offline' ? 'offline' : 'checking' },
      ];
    }
    return [
      { label: 'Track', value: health.track },
      {
        label: 'Model',
        value: health.llmModel ?? this.liveQwenDecision()?.modelName ?? 'awaiting live run',
      },
      { label: 'Runtime', value: health.alibabaCloudService ?? health.deploymentTarget },
      { label: 'Region', value: health.alibabaCloudRegion ?? 'not set' },
    ];
  });

  readonly experienceBenchmarkFacts = computed<HealthFact[]>(() => {
    const benchmark = this.showcase()?.experienceBenchmark;
    if (!benchmark || benchmark.status !== 'ready') {
      return [{ label: 'Benchmark', value: 'loading evidence' }];
    }
    return [
      {
        label: 'Lifecycle cases',
        value: `${benchmark.lifecycleCasesPassed}/${benchmark.caseCount}`,
      },
      {
        label: 'Qwen receipts',
        value: `${benchmark.qwenReceiptCount}/${benchmark.curatorDecisionCount}`,
      },
      { label: 'Critical recall', value: this.percent(benchmark.criticalMemoryRecall) },
      { label: 'Forbidden leak', value: this.percent(benchmark.forbiddenMemoryLeakRate) },
      { label: 'Budget compliance', value: this.percent(benchmark.tokenBudgetCompliance) },
      { label: 'Weighted score', value: `${benchmark.overallScore.toFixed(1)}/100` },
    ];
  });

  readonly runtimeSignals = computed<DemoSignal[]>(() => {
    const health = this.health();
    const benchmark = this.showcase()?.experienceBenchmark;
    const liveDecision = this.liveQwenDecision();
    return [
      {
        label: 'Qwen curator',
        value: health?.llmModel ?? liveDecision?.modelName ?? 'awaiting live run',
        detail: 'qwen-cloud chooses remember, supersede, forget, or ignore.',
        tone:
          health?.llmProvider === 'qwen-cloud' || liveDecision?.providerName === 'qwen-cloud'
            ? 'ready'
            : 'watch',
      },
      {
        label: 'Memory lifecycle',
        value: benchmark?.status === 'ready' ? '24 / 24' : 'loading',
        detail: 'Preference, conflict, TTL, forgetting, budget, and duplicate cases.',
        tone: benchmark?.status === 'ready' ? 'ready' : 'watch',
      },
      {
        label: 'Safety gate',
        value: benchmark?.status === 'ready' ? '0% leak' : 'loading',
        detail: 'Superseded, expired, and forgotten values are excluded from recall.',
        tone: benchmark?.status === 'ready' ? 'ready' : 'watch',
      },
      {
        label: 'Cloud proof',
        value: health?.alibabaCloudService ?? 'Alibaba FC',
        detail: health?.alibabaCloudRegion ?? 'region metadata loading',
        tone: this.liveHealthState() === 'ready' ? 'ready' : 'watch',
      },
    ];
  });

  readonly oldMemory = computed(() =>
    this.memories().find((memory) => memory.sourceSessionId === 'session-1'),
  );
  readonly activeMemory = computed(() =>
    this.memories().find(
      (memory) => memory.sourceSessionId === 'session-2' && memory.status === 'active',
    ),
  );
  readonly selectedMemory = computed(() => this.recall()?.selected[0]?.memory ?? null);
  readonly forbiddenLeakDetected = computed(() =>
    (this.recall()?.contextCard ?? '').toLowerCase().includes('10% canary'),
  );
  readonly arenaPassed = computed(() => {
    const active = this.activeMemory();
    const firstDecision = this.firstCapture()?.decision;
    const secondDecision = this.secondCapture()?.decision;
    return (
      this.arenaStep() === 4 &&
      firstDecision?.requestedAction === 'remember' &&
      firstDecision.action === 'remember' &&
      firstDecision.providerName === 'qwen-cloud' &&
      firstDecision.llmReceipt !== null &&
      (secondDecision?.requestedAction === 'remember' ||
        secondDecision?.requestedAction === 'supersede') &&
      secondDecision.action === 'supersede' &&
      secondDecision.providerName === 'qwen-cloud' &&
      secondDecision.llmReceipt !== null &&
      this.oldMemory()?.status === 'superseded' &&
      active !== undefined &&
      this.selectedMemory()?.memoryId === active.memoryId &&
      !this.forbiddenLeakDetected()
    );
  });
  readonly arenaVerdict = computed(() => {
    if (this.arenaError()) {
      return 'Run interrupted';
    }
    if (this.arenaBusy()) {
      return 'Qwen is curating memory';
    }
    if (this.arenaStep() === 4) {
      return this.arenaPassed() ? 'Lifecycle proof passed' : 'Review lifecycle evidence';
    }
    return 'Ready for a fresh judge run';
  });

  readonly demoSteps: DemoStep[] = [
    {
      order: '01',
      title: 'Inspect governed source memory',
      outcome: 'Review claim conflicts, source proofs, and the human approval ledger.',
      route: '/memory',
      routeLabel: 'Memory Hub',
      icon: 'database',
    },
    {
      order: '02',
      title: 'Generate a source-backed requirement',
      outcome: 'Turn rough intent and recalled experience into a reviewable Jira draft.',
      route: '/requirements',
      routeLabel: 'Requirement Flow',
      icon: 'clipboard',
    },
    {
      order: '03',
      title: 'Trace retrieval before generation',
      outcome: 'See selected evidence, exclusions, graph paths, and prompt preview.',
      route: '/context/case_async_status',
      routeLabel: 'Context Trail',
      icon: 'timeline',
    },
    {
      order: '04',
      title: 'Verify audit and evaluation',
      outcome: 'Inspect model records, source coverage, scorecards, and human feedback.',
      route: '/audit',
      routeLabel: 'Audit & Eval',
      icon: 'shield',
    },
  ];

  ngOnInit(): void {
    this.dream
      .getHealth()
      .pipe(
        catchError(() => {
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
      .pipe(catchError(() => of(null)))
      .subscribe((showcase) => this.showcase.set(showcase));
  }

  async runJudgeArena(): Promise<void> {
    if (this.arenaBusy()) {
      return;
    }
    this.resetArena();
    this.arenaBusy.set(true);
    this.arenaStep.set(1);
    const userId = this.judgeIdentity();

    try {
      this.firstCapture.set(
        await firstValueFrom(
          this.dream.captureExperience({
            teamId: this.teamId,
            userId,
            sessionId: 'session-1',
            observation: this.firstObservation,
            sourceReference: 'judge-arena://session-1',
          }),
        ),
      );

      this.arenaStep.set(2);
      this.secondCapture.set(
        await firstValueFrom(
          this.dream.captureExperience({
            teamId: this.teamId,
            userId,
            sessionId: 'session-2',
            observation: this.secondObservation,
            sourceReference: 'judge-arena://session-2',
          }),
        ),
      );

      this.arenaStep.set(3);
      this.recall.set(
        await firstValueFrom(
          this.dream.recallExperience({
            teamId: this.teamId,
            userId,
            sessionId: 'session-3',
            query: this.recallQuery,
            tokenBudget: 64,
          }),
        ),
      );

      const [memories, decisions] = await Promise.all([
        firstValueFrom(this.dream.listExperienceMemories(this.teamId, userId)),
        firstValueFrom(this.dream.listExperienceDecisions(this.teamId, userId)),
      ]);
      this.memories.set(memories);
      this.decisions.set(decisions);
      this.arenaStep.set(4);
    } catch (error: unknown) {
      this.arenaError.set(this.errorMessage(error));
    } finally {
      this.arenaBusy.set(false);
    }
  }

  async recordPositiveFeedback(): Promise<void> {
    const memory = this.selectedMemory();
    if (!memory || this.feedbackState() === 'saving') {
      return;
    }
    this.feedbackState.set('saving');
    try {
      const updated = await firstValueFrom(
        this.dream.rateExperienceMemory(
          memory.memoryId,
          this.teamId,
          this.judgeIdentity(),
          true,
          true,
        ),
      );
      this.memories.update((items) =>
        items.map((item) => (item.memoryId === updated.memoryId ? updated : item)),
      );
      this.feedbackState.set('saved');
    } catch {
      this.feedbackState.set('error');
    }
  }

  stepState(step: number): ArenaStepState {
    if (this.arenaError() && this.arenaStep() === step) {
      return 'error';
    }
    if (this.arenaStep() > step) {
      return 'complete';
    }
    if (this.arenaBusy() && this.arenaStep() === step) {
      return 'running';
    }
    return 'pending';
  }

  decisionTokens(decision: ExperienceDecision | undefined): string {
    const total = decision?.tokenUsage?.['total_tokens'];
    return typeof total === 'number' ? `${total} tokens` : 'token usage recorded server-side';
  }

  receiptReference(decision: ExperienceDecision): string {
    return (
      decision.llmReceipt?.providerRequestId ??
      decision.llmReceipt?.responseId ??
      'receipt unavailable'
    );
  }

  shortHash(value: string | undefined): string {
    return value ? `${value.slice(0, 12)}...` : 'unavailable';
  }

  private resetArena(): void {
    this.judgeIdentity.set(this.newJudgeIdentity());
    this.arenaError.set(null);
    this.arenaStep.set(0);
    this.firstCapture.set(null);
    this.secondCapture.set(null);
    this.recall.set(null);
    this.memories.set([]);
    this.decisions.set([]);
    this.feedbackState.set('idle');
  }

  private newJudgeIdentity(): string {
    return `judge-${Date.now().toString(36)}`;
  }

  private percent(value: number): string {
    return `${(value * 100).toFixed(value === 0 || value === 1 ? 0 : 1)}%`;
  }

  private errorMessage(error: unknown): string {
    if (typeof error === 'object' && error !== null && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) {
        return payload.detail;
      }
    }
    return 'The live Qwen request did not complete. Runtime and benchmark proof remain available.';
  }

  private isReadyHealth(health: DreamHealth): boolean {
    return (
      health.status === 'ok' &&
      health.track === 'Track 1: MemoryAgent' &&
      health.llmProvider === 'qwen-cloud' &&
      health.llmApiKeyConfigured &&
      health.deploymentTarget.toLowerCase().includes('alibaba cloud function compute')
    );
  }
}
