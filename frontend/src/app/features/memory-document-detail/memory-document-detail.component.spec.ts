// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { DreamApiService, IntakeDocumentDetail } from '../../core/dream-api.service';
import { MemoryDocumentDetailComponent } from './memory-document-detail.component';

describe('MemoryDocumentDetailComponent', () => {
  it('keeps technical provenance behind disclosure while presenting distilled knowledge', async () => {
    const detail = {
      document: {
        documentId: 'intake-test',
        teamId: 'demo_team',
        title: 'Forecast Recovery Note',
        documentType: 'runbooks',
        originalPath: 'uploaded://forecast-recovery.txt',
        storedPath: 'artifacts/intake/uploads/intake-test.txt',
        sourceHash: 'sha256:secret',
        promotedPath: 'knowledge_packs/demo_team/docs/runbooks/forecast-recovery.md',
        status: 'promoted',
        createdAt: '2026-07-11T12:00:00Z',
        updatedAt: '2026-07-11T12:05:00Z',
        warnings: [],
      },
      draft: {
        draftId: 'draft-intake-test',
        documentId: 'intake-test',
        teamId: 'demo_team',
        title: 'Forecast Recovery Note',
        targetDocType: 'runbooks',
        app: 'ForecastDemo',
        component: 'job-execution',
        sections: [
          {
            sectionId: 'section-1',
            heading: 'Recovery behavior',
            level: 1,
            text: 'Retry requires human review.',
            concepts: ['retry', 'human review'],
            sourceSpan: { startLine: 1, endLine: 4 },
          },
        ],
        concepts: [{ concept: 'retry', sourceSections: ['section-1'], confidence: 0.8 }],
        reviewStatus: 'promoted',
        reviewer: 'Demo Reviewer',
        reviewNotes: 'Approved for testing.',
        normalizedMarkdown: 'intake_document_id: intake-test\nsource_hash: sha256:secret',
        warnings: [],
      },
      rawText: '# Forecast Recovery Note',
      rawTextTruncated: false,
      rawSizeBytes: 24,
      rawTextAvailable: true,
      sourceHashVerified: true,
      auditEvents: [],
      reviewEvents: [
        {
          eventId: 'review-1',
          eventType: 'review',
          draftId: 'draft-intake-test',
          documentId: 'intake-test',
          teamId: 'demo_team',
          createdAt: '2026-07-11T12:04:00Z',
          reviewer: 'Demo Reviewer',
          previousStatus: 'approved',
          newStatus: 'promoted',
          auditRunId: 'audit-1',
          metadataSnapshot: {
            title: 'Forecast Recovery Note',
            targetDocType: 'runbooks',
            app: 'ForecastDemo',
            component: 'job-execution',
            concepts: ['retry'],
            reviewStatus: 'promoted',
          },
          metadataDiff: [
            { field: 'review_status', before: 'approved', after: 'promoted' },
            { field: 'promoted_path', before: null, after: 'knowledge_packs/private/path.md' },
          ],
          sectionHashes: [],
          warnings: [],
        },
      ],
      downstreamEvents: [],
      downstreamUsages: [],
    } as IntakeDocumentDetail;

    await TestBed.configureTestingModule({
      imports: [MemoryDocumentDetailComponent],
      providers: [
        { provide: DreamApiService, useValue: { getIntakeDocumentDetail: () => of(detail) } },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: convertToParamMap({ documentId: 'intake-test' }) },
            paramMap: of(convertToParamMap({ documentId: 'intake-test' })),
          },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(MemoryDocumentDetailComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    expect(compiled.textContent).toContain('Available to AI workflows');
    expect(compiled.querySelectorAll('.lifecycle li.complete')).toHaveSize(4);
    expect(compiled.querySelector('.distilled-document')?.textContent).not.toContain('sha256:');
    expect(compiled.querySelector('.technical-disclosure')?.hasAttribute('open')).toBeFalse();
    expect(compiled.querySelector('.activity-grid')?.textContent).not.toContain('knowledge_packs/private');
  });
});
