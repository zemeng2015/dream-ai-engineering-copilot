// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';

import { EvidenceSearchPanelComponent } from './evidence-search-panel.component';

describe('EvidenceSearchPanelComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvidenceSearchPanelComponent],
    }).compileComponents();
  });

  it('explains repository retrieval without presenting candidates as task conclusions', () => {
    const fixture = TestBed.createComponent(EvidenceSearchPanelComponent);
    fixture.componentRef.setInput('query', 'status tracking output collector tests');
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';

    expect(text).toContain('Repository Retrieval Preview');
    expect(text).toContain('These are candidates, not task conclusions.');
    expect(text).toContain('status tracking output collector tests');
    expect(text).not.toContain('Evidence Search');
  });
});
