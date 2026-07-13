// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { DreamApiService, MemoryClaimSource } from '../../core/dream-api.service';
import { MemoryClaimSourceReviewComponent } from './memory-claim-source-review.component';

describe('MemoryClaimSourceReviewComponent', () => {
  it('loads the exact claim source and highlights its recorded evidence lines', async () => {
    const source: MemoryClaimSource = {
      teamId: 'demo_team',
      scanId: 'scan-1',
      claimId: 'claim-1',
      sourceId: 'source-1',
      sourceType: 'code',
      sourcePath: 'src/status-tracker.ts',
      fileName: 'status-tracker.ts',
      content: 'line one\nline two\nline three',
      contentTruncated: false,
      sizeBytes: 28,
      lineCount: 3,
      contentHash: 'sha256:1234567890abcdef',
      indexedAt: '2026-07-13T12:00:00Z',
      trustLevel: 'team',
      commitSha: 'abc123',
      spans: [
        {
          spanId: 'span-1',
          startLine: 2,
          endLine: 3,
          excerptHash: 'sha256:fedcba0987654321',
        },
      ],
    };

    await TestBed.configureTestingModule({
      imports: [MemoryClaimSourceReviewComponent],
      providers: [
        { provide: DreamApiService, useValue: { getMemoryClaimSource: () => of(source) } },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              queryParamMap: convertToParamMap({
                teamId: 'demo_team',
                scanId: 'scan-1',
                claimId: 'claim-1',
                sourcePath: 'src/status-tracker.ts',
              }),
            },
          },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(MemoryClaimSourceReviewComponent);
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;

    expect(element.textContent).toContain('status-tracker.ts');
    expect(element.textContent).toContain('L2-L3');
    expect(element.querySelectorAll('.source-line.evidence-line')).toHaveSize(2);
    expect(element.textContent).toContain('Complete preview');
  });
});
