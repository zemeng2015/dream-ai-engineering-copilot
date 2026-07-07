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
      deployment_target: 'Alibaba Cloud Function Compute custom container',
      alibaba_cloud_region: 'ap-southeast-1',
      alibaba_cloud_service: 'Function Compute custom container',
      llm_provider: 'qwen-cloud',
      llm_model: 'qwen3.7-plus',
      llm_base_url: 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',
      llm_api_key_configured: true,
      proof_file: 'deploy/alibaba/serverless-devs.yaml',
    });
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';

    expect(text).toContain('Track 1: MemoryAgent');
    expect(text).toContain('qwen-cloud');
    expect(text).toContain('qwen3.7-plus');
    expect(text).toContain('Live Qwen proof ready');
    expect(text).toContain('Alibaba Cloud Function Compute custom container');
    expect(text).toContain('ap-southeast-1');
    expect(text).toContain('API key configured');
    expect(text).toContain('deploy/alibaba/serverless-devs.yaml');
    expect(text).toContain('Public video URL');
    expect(text).toContain('Alibaba deployment proof');
    expect(text).toContain('Judging Scorecard Alignment');
    expect(text).toContain('55/100');
    expect(text).toContain('Innovation and AI Creativity');
    expect(text).toContain('Technical Depth and Engineering');
    expect(text).toContain('Presentation and Documentation');
    expect(text).toContain('Live inputs');
  });

  it('keeps the judge route usable when the backend is offline', () => {
    const fixture = TestBed.createComponent(HackathonDemoComponent);
    fixture.detectChanges();
    const request = httpTesting.expectOne('http://127.0.0.1:8000/health');

    request.flush({ message: 'offline' }, { status: 503, statusText: 'Service Unavailable' });
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
