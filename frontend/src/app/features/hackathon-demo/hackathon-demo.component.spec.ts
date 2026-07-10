// SPDX-License-Identifier: Apache-2.0

import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { HackathonDemoComponent } from './hackathon-demo.component';

interface CaptureFixture {
  decision: Record<string, unknown>;
  memory: Record<string, unknown>;
  affected_memories: Record<string, unknown>[];
  active_memory_count: number;
}

describe('HackathonDemoComponent', () => {
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HackathonDemoComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('renders Qwen Cloud hackathon proof signals with live health metadata', () => {
    const fixture = TestBed.createComponent(HackathonDemoComponent);
    fixture.detectChanges();
    const request = httpTesting.expectOne('http://127.0.0.1:8000/health');

    expect(request.request.method).toBe('GET');

    request.flush({
      status: 'ok',
      service: 'dream-memoryagent-api',
      track: 'Track 1: MemoryAgent',
      deployment_target: 'Alibaba Cloud Function Compute custom runtime',
      alibaba_cloud_region: 'ap-southeast-1',
      alibaba_cloud_service: 'Function Compute custom runtime',
      llm_provider: 'qwen-cloud',
      llm_model: 'qwen3.7-plus',
      llm_base_url: 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',
      llm_api_key_configured: true,
      proof_file: 'deploy/alibaba/serverless-devs-runtime.yaml',
    });
    const showcaseRequest = httpTesting.expectOne('http://127.0.0.1:8000/qwencloud/showcase');

    expect(showcaseRequest.request.method).toBe('GET');

    showcaseRequest.flush({
      generated_at: '2026-07-07T18:20:00Z',
      project_title: 'DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence',
      track: 'Track 1: MemoryAgent',
      elevator_pitch: 'Source-backed engineering memory for Qwen Cloud.',
      runtime: {
        status: 'ok',
        service: 'dream-memoryagent-api',
        track: 'Track 1: MemoryAgent',
        deployment_target: 'Alibaba Cloud Function Compute custom runtime',
        alibaba_cloud_region: 'ap-southeast-1',
        alibaba_cloud_service: 'Function Compute custom runtime',
        llm_provider: 'qwen-cloud',
        llm_model: 'qwen3.7-plus',
        llm_api_key_configured: true,
        proof_file: 'deploy/alibaba/serverless-devs-runtime.yaml',
        qwen_cloud_ready: true,
        alibaba_runtime_ready: true,
        live_backend_ready: true,
      },
      judge_flow: [],
      evidence: [],
      benchmark: {
        status: 'ready',
        run_id: '20260709T215947Z',
        provider: 'qwen-cloud',
        model: 'qwen3.7-plus',
        case_count: 7,
        baseline_score: 25.3,
        dream_score: 48.7,
        score_delta: 23.4,
        median_delta: 23.2,
        exact_paired_permutation_p: 0.0156,
        dream_wins: 7,
        exact_retrieval_recall_at_12: 0.356,
        report_path:
          'artifacts/qwencloud-proof/qwen-memory-ab-benchmark-20260709T215947Z.json',
        limitations: ['Seven synthetic engineering cases.'],
      },
      experience_benchmark: {
        status: 'ready',
        run_id: '20260710T045527Z',
        provider: 'qwen-cloud',
        model: 'qwen3.7-plus',
        case_count: 24,
        decision_count: 37,
        passed_cases: 24,
        proposal_accuracy: 1,
        action_accuracy: 1,
        critical_memory_recall: 1,
        forbidden_memory_leak_rate: 0,
        token_budget_compliance: 1,
        memory_payload_accuracy: 1,
        exact_canonical_key_accuracy: 0.5135,
        overall_score: 100,
        report_path: 'docs/assets/qwen-experience-memory-benchmark-report.json',
        limitations: ['Synthetic lifecycle scenarios.'],
      },
      scorecard: {
        weighted_current_evidence_ready: 85,
        weighted_static_evidence_ready: 100,
        weighted_total: 100,
        live_backend_points: 30,
        public_video_points: 0,
        missing_external_inputs: ['public_demo_video_url'],
      },
    });
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';

    expect(text).toContain('Track 1: MemoryAgent');
    expect(text).toContain('qwen-cloud');
    expect(text).toContain('qwen3.7-plus');
    expect(text).toContain('Qwen + Alibaba runtime verified');
    expect(text).toContain('ap-southeast-1');
    expect(text).toContain('Three sessions. One current truth.');
    expect(text).toContain('24 / 24');
    expect(text).toContain('24/24');
    expect(text).toContain('37');
    expect(text).toContain('100.0/100');
    expect(text).toContain('0% leak');
    expect(text).toContain('Run Live 3-Session Proof');
  });

  it('keeps the judge route usable when the backend is offline', () => {
    const fixture = TestBed.createComponent(HackathonDemoComponent);
    fixture.detectChanges();
    const request = httpTesting.expectOne('http://127.0.0.1:8000/health');

    request.flush({ message: 'offline' }, { status: 503, statusText: 'Service Unavailable' });
    const showcaseRequest = httpTesting.expectOne('http://127.0.0.1:8000/qwencloud/showcase');
    showcaseRequest.flush(
      { message: 'offline' },
      { status: 503, statusText: 'Service Unavailable' },
    );
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';

    expect(text).toContain('Live runtime unavailable');
    expect(text).toContain('Three sessions. One current truth.');
  });

  it('runs the live remember, supersede, and limited-recall sequence', async () => {
    const fixture = TestBed.createComponent(HackathonDemoComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    flushMinimalBoot(httpTesting);

    const runPromise = component.runJudgeArena();
    const firstRequest = httpTesting.expectOne('http://127.0.0.1:8000/experience/capture');
    const userId = firstRequest.request.body.user_id as string;
    expect(firstRequest.request.body.session_id).toBe('session-1');
    expect(firstRequest.request.body.llm_provider).toBe('qwen-cloud');
    firstRequest.flush(captureResponse('remember', userId, 'memory-old', 'session-1'));
    await settleAsyncWork();

    const secondRequest = httpTesting.expectOne('http://127.0.0.1:8000/experience/capture');
    expect(secondRequest.request.body.session_id).toBe('session-2');
    secondRequest.flush(captureResponse('supersede', userId, 'memory-new', 'session-2'));
    await settleAsyncWork();

    const recallRequest = httpTesting.expectOne('http://127.0.0.1:8000/experience/recall');
    expect(recallRequest.request.body.session_id).toBe('session-3');
    expect(recallRequest.request.body.token_budget).toBe(64);
    recallRequest.flush({
      team_id: 'qwencloud-judge-arena',
      user_id: userId,
      session_id: 'session-3',
      query: 'current canary rollout',
      token_budget: 64,
      estimated_tokens_used: 22,
      selected: [
        {
          memory: memoryResponse(userId, 'memory-new', 'session-2', 'active'),
          score: 14.4,
          estimated_tokens: 22,
          selected: true,
          reason: 'Current preference fits the query and token budget.',
        },
      ],
      excluded: [],
      expired_memory_ids: [],
      context_card: '- preference:canary_rollout = use a 20% canary for 45 minutes\n',
    });
    await settleAsyncWork();

    const memoryRequest = httpTesting.expectOne(
      (request) => request.url === 'http://127.0.0.1:8000/experience/memories',
    );
    const decisionRequest = httpTesting.expectOne(
      (request) => request.url === 'http://127.0.0.1:8000/experience/decisions',
    );
    memoryRequest.flush([
      memoryResponse(userId, 'memory-old', 'session-1', 'superseded'),
      memoryResponse(userId, 'memory-new', 'session-2', 'active'),
    ]);
    decisionRequest.flush([
      captureResponse('remember', userId, 'memory-old', 'session-1').decision,
      captureResponse('supersede', userId, 'memory-new', 'session-2').decision,
    ]);
    await runPromise;
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(component.arenaPassed()).toBeTrue();
    expect(text).toContain('Lifecycle proof passed');
    expect(text).toContain('superseded');
    expect(text).toContain('20% canary');
    expect(text).toContain('22 / 64');
    expect(text).toContain('Old value leaked');
    expect(text).toContain('no');
  });

  it('exposes the guided judge flow routes', () => {
    const fixture = TestBed.createComponent(HackathonDemoComponent);
    const component = fixture.componentInstance;

    expect(component.demoSteps.map((step) => step.route)).toEqual([
      '/memory',
      '/requirements',
      '/context/case_async_status',
      '/audit',
    ]);
  });
});

async function settleAsyncWork(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

function flushMinimalBoot(httpTesting: HttpTestingController): void {
  httpTesting.expectOne('http://127.0.0.1:8000/health').flush({
    status: 'ok',
    service: 'dream-memoryagent-api',
    track: 'Track 1: MemoryAgent',
    deployment_target: 'Alibaba Cloud Function Compute custom runtime',
    alibaba_cloud_region: 'ap-southeast-1',
    alibaba_cloud_service: 'Function Compute custom runtime',
    llm_provider: 'qwen-cloud',
    llm_model: 'qwen3.7-plus',
    llm_api_key_configured: true,
    proof_file: 'deploy/alibaba/serverless-devs-runtime.yaml',
  });
  httpTesting.expectOne('http://127.0.0.1:8000/qwencloud/showcase').flush({
    generated_at: '2026-07-10T05:00:00Z',
    project_title: 'DREAM MemoryAgent',
    track: 'Track 1: MemoryAgent',
    elevator_pitch: 'Cross-session experience memory.',
    runtime: {
      status: 'ok',
      service: 'dream-memoryagent-api',
      track: 'Track 1: MemoryAgent',
      deployment_target: 'Alibaba Cloud Function Compute custom runtime',
      alibaba_cloud_region: 'ap-southeast-1',
      alibaba_cloud_service: 'Function Compute custom runtime',
      llm_provider: 'qwen-cloud',
      llm_model: 'qwen3.7-plus',
      llm_api_key_configured: true,
      proof_file: 'deploy/alibaba/serverless-devs-runtime.yaml',
      qwen_cloud_ready: true,
      alibaba_runtime_ready: true,
      live_backend_ready: true,
    },
    judge_flow: [],
    evidence: [],
    benchmark: {
      status: 'ready',
      case_count: 7,
      baseline_score: 25.3,
      dream_score: 48.7,
      score_delta: 23.4,
      median_delta: 23.2,
      dream_wins: 7,
      exact_retrieval_recall_at_12: 0.356,
      limitations: [],
    },
    experience_benchmark: {
      status: 'ready',
      case_count: 24,
      decision_count: 37,
      passed_cases: 24,
      proposal_accuracy: 1,
      action_accuracy: 1,
      critical_memory_recall: 1,
      forbidden_memory_leak_rate: 0,
      token_budget_compliance: 1,
      memory_payload_accuracy: 1,
      exact_canonical_key_accuracy: 0.5135,
      overall_score: 100,
      limitations: [],
    },
    scorecard: {
      weighted_current_evidence_ready: 100,
      weighted_static_evidence_ready: 100,
      weighted_total: 100,
      live_backend_points: 30,
      public_video_points: 15,
      missing_external_inputs: [],
    },
  });
}

function memoryResponse(
  userId: string,
  memoryId: string,
  sessionId: string,
  status: 'active' | 'superseded',
): Record<string, unknown> {
  return {
    memory_id: memoryId,
    team_id: 'qwencloud-judge-arena',
    user_id: userId,
    kind: 'preference',
    key: 'canary_rollout',
    value:
      sessionId === 'session-1'
        ? 'use a 10% canary for 30 minutes'
        : 'use a 20% canary for 45 minutes',
    status,
    confidence: 0.98,
    importance: 4,
    source_session_id: sessionId,
    source_reference: `judge-arena://${sessionId}`,
    created_at: '2026-07-10T05:00:00Z',
    updated_at: '2026-07-10T05:01:00Z',
    valid_from: '2026-07-10T05:00:00Z',
    valid_until: null,
    superseded_by: status === 'superseded' ? 'memory-new' : null,
    last_recalled_at: status === 'active' ? '2026-07-10T05:02:00Z' : null,
    recall_count: status === 'active' ? 1 : 0,
    feedback_count: 0,
    helpful_total: 0,
    correctness_total: 0,
  };
}

function captureResponse(
  action: 'remember' | 'supersede',
  userId: string,
  memoryId: string,
  sessionId: string,
): CaptureFixture {
  return {
    decision: {
      decision_id: `decision-${sessionId}`,
      team_id: 'qwencloud-judge-arena',
      user_id: userId,
      session_id: sessionId,
      requested_action: action,
      action,
      target_memory_id: action === 'supersede' ? 'memory-old' : null,
      created_memory_id: memoryId,
      rationale: action === 'remember' ? 'Durable user preference.' : 'New preference replaces old.',
      provider_name: 'qwen-cloud',
      model_name: 'qwen3.7-plus',
      token_usage: { total_tokens: 180 },
      created_at: '2026-07-10T05:00:00Z',
    },
    memory: memoryResponse(userId, memoryId, sessionId, 'active'),
    affected_memories:
      action === 'supersede'
        ? [memoryResponse(userId, 'memory-old', 'session-1', 'superseded')]
        : [],
    active_memory_count: 1,
  };
}
