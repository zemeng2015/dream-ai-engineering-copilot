// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { HackathonDemoComponent } from './hackathon-demo.component';

describe('HackathonDemoComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HackathonDemoComponent],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('renders Qwen Cloud hackathon proof signals', () => {
    const fixture = TestBed.createComponent(HackathonDemoComponent);
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';

    expect(text).toContain('Track 1: MemoryAgent');
    expect(text).toContain('qwen-cloud');
    expect(text).toContain('deploy/alibaba/serverless-devs.yaml');
    expect(text).toContain('Public video URL');
    expect(text).toContain('Alibaba deployment proof');
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
