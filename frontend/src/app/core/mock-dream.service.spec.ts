import { TestBed } from '@angular/core/testing';

import { MockDreamService } from './mock-dream.service';

describe('MockDreamService', () => {
  let service: MockDreamService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(MockDreamService);
  });

  it('searches knowledge chunks deterministically', () => {
    const first = service.searchKnowledge({ query: 'job execution failure', topK: 3 });
    const second = service.searchKnowledge({ query: 'job execution failure', topK: 3 });

    expect(first.length).toBeGreaterThan(0);
    expect(first.map((chunk) => chunk.id)).toEqual(second.map((chunk) => chunk.id));
    expect(first[0].title).toContain('Job');
  });

  it('generates a requirement draft and creates an audit run', () => {
    const before = service.auditRuns().length;

    const result = service.draftRequirement({
      teamId: 'demo_team',
      app: 'BatchJobDemo',
      component: 'job-execution',
      roughBusinessRequest: 'Add async status tracking',
      topK: 5,
    });

    expect(result.markdown).toContain('This is a draft for human review.');
    expect(result.sourcesUsed.length).toBeGreaterThan(0);
    expect(service.auditRuns().length).toBe(before + 1);
  });

  it('generates a PR review aid with human review warning', () => {
    const result = service.reviewPr({
      teamId: 'demo_team',
      app: 'BatchJobDemo',
      component: 'job-execution',
      diffText: '+ startJob\n+ statusForJob',
      jiraContext: 'Add async status tracking',
      topK: 5,
    });

    expect(result.markdown).toContain('Human review is required');
    expect(result.risk).toBe('Low');
    expect(result.warnings.length).toBeGreaterThan(0);
  });

  it('keeps TestGen stub safe and does not generate files', () => {
    const result = service.runTestGenStub({
      teamId: 'demo_team',
      repoPath: 'examples/java-demo-repo',
      targetLanguage: 'java',
      dryRun: true,
    });

    expect(result.status).toBe('stub_only');
    expect(result.generatedFiles).toEqual([]);
    expect(result.reportMarkdown).toContain('No unit tests were generated');
  });

  it('stores human ratings against mock runs', () => {
    const rating = service.addRating({
      runId: 'run_20260619_0011',
      usefulnessScore: 5,
      correctnessScore: 4,
      comments: 'Useful mock workflow',
    });

    expect(rating.createdAt).toBeTruthy();
    expect(service.ratings()[0].comments).toBe('Useful mock workflow');
  });
});

