// SPDX-License-Identifier: Apache-2.0

import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { HackathonDemoComponent } from './hackathon-demo.component';

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
    expect(text).toContain('Live Qwen proof ready');
    expect(text).toContain('Alibaba Cloud Function Compute custom runtime');
    expect(text).toContain('ap-southeast-1');
    expect(text).toContain('API key configured');
    expect(text).toContain('deploy/alibaba/serverless-devs-runtime.yaml');
    expect(text).toContain('Live Evidence');
    expect(text).toContain('Qwen Cloud execution');
    expect(text).toContain('Alibaba Function Compute');
    expect(text).toContain('Measured Qwen memory lift');
    expect(text).toContain('25.3 to 48.7');
    expect(text).toContain('+23.4');
    expect(text).toContain('7/7');
    expect(text).toContain('0.0156');
    expect(text).toContain('35.6%');
    expect(text).toContain('synthetic engineering cases');
    expect(text).toContain('Judging Scorecard Alignment');
    expect(text).toContain('Innovation and AI Creativity');
    expect(text).toContain('Technical Depth and Engineering');
    expect(text).toContain('Presentation and Documentation');
    expect(text).toContain('Live proof ready');
    expect(text).not.toContain('Public video URL');
    expect(text).not.toContain('Local Proof Commands');
    expect(text).not.toContain('Final Submit Gate');
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

    expect(text).toContain('Backend offline');
    expect(text).toContain('waiting for backend');
    expect(text).toContain('Five-minute Judge Flow');
  });

  it('exposes the guided judge flow routes', () => {
    const fixture = TestBed.createComponent(HackathonDemoComponent);
    const component = fixture.componentInstance;

    expect(component.demoSteps.map((step) => step.route)).toEqual([
      '/memory',
      '/requirements',
      '/context/case_async_status',
      '/codebase',
      '/audit',
    ]);
  });
});
