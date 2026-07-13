// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';

import { IndexJsonPanelComponent } from './index-json-panel.component';

describe('IndexJsonPanelComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IndexJsonPanelComponent],
    }).compileComponents();
  });

  it('explains the selected file as repository memory and hides raw JSON by default', () => {
    const fixture = TestBed.createComponent(IndexJsonPanelComponent);
    fixture.componentRef.setInput('repoIndexPath', 'artifacts/codebase-indexes/demo/repo.json');
    fixture.componentRef.setInput('selectedFileJson', '{"path":"src/status.ts"}');
    fixture.componentRef.setInput('selectedFile', {
      fileId: 'file-1',
      path: 'src/status.ts',
      language: 'typescript',
      sizeBytes: 512,
      lineCount: 20,
      role: 'source',
      summary: 'Tracks status.',
      symbols: ['StatusTracker'],
      concepts: ['execution status'],
    });
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    const text = element.textContent ?? '';

    expect(text).toContain('Repository Memory Record');
    expect(text).toContain('Structured memory node');
    expect(text).toContain('Graph-ready repository node');
    expect(text).toContain('Retrievable evidence');
    expect(text).not.toContain('JSON Index');
    expect(element.querySelector<HTMLDetailsElement>('details')?.open).toBeFalse();
  });
});
