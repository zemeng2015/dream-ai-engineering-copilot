// SPDX-License-Identifier: Apache-2.0

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CodebaseIndexFile } from '../../core/dream-api.service';
import { RepoBrowserPanelComponent } from './repo-browser-panel.component';

describe('RepoBrowserPanelComponent', () => {
  let fixture: ComponentFixture<RepoBrowserPanelComponent>;

  const files: CodebaseIndexFile[] = [
    {
      fileId: 'root-readme',
      path: 'README.md',
      language: 'markdown',
      sizeBytes: 100,
      lineCount: 4,
      role: 'docs',
      summary: 'Repository overview.',
      symbols: [],
      concepts: [],
    },
    {
      fileId: 'status-file',
      path: 'src/app/status-tracker.ts',
      language: 'typescript',
      sizeBytes: 200,
      lineCount: 12,
      role: 'source',
      summary: 'Tracks execution status.',
      symbols: ['StatusTracker'],
      concepts: ['execution status'],
    },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RepoBrowserPanelComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(RepoBrowserPanelComponent);
  });

  it('renders an IDE-style hierarchy and expands ancestors of the selected file', () => {
    fixture.componentRef.setInput('repoName', 'demo-repo');
    fixture.componentRef.setInput('repoPath', 'examples/demo-repo');
    fixture.componentRef.setInput('files', files);
    fixture.componentRef.setInput('selectedFilePath', 'src/app/status-tracker.ts');
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;

    expect(element.querySelector<HTMLElement>('[title="src"]')?.getAttribute('aria-expanded')).toBe('true');
    expect(element.querySelector<HTMLElement>('[title="src/app"]')?.getAttribute('aria-expanded')).toBe('true');
    expect(element.querySelector<HTMLElement>('[title="src/app/status-tracker.ts"]')?.classList).toContain('active');
    expect(element.textContent).toContain('README.md');
    expect(element.textContent).toContain('status-tracker.ts');
  });

  it('collapses a folder without changing the selected file', () => {
    fixture.componentRef.setInput('repoName', 'demo-repo');
    fixture.componentRef.setInput('files', files);
    fixture.componentRef.setInput('selectedFilePath', 'src/app/status-tracker.ts');
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    element.querySelector<HTMLButtonElement>('[title="src"]')?.click();
    fixture.detectChanges();

    expect(element.querySelector('[title="src/app"]')).toBeNull();
    expect(element.querySelector('[title="src/app/status-tracker.ts"]')).toBeNull();
  });
});
