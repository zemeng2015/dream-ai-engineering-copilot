// SPDX-License-Identifier: Apache-2.0

import { FormControl, FormGroup } from '@angular/forms';
import { TestBed } from '@angular/core/testing';

import { CodebaseIndexControlsComponent } from './codebase-index-controls.component';

describe('CodebaseIndexControlsComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CodebaseIndexControlsComponent],
    }).compileComponents();
  });

  it('leads with a user query and keeps repository maintenance in advanced settings', () => {
    const fixture = TestBed.createComponent(CodebaseIndexControlsComponent);
    fixture.componentRef.setInput(
      'form',
      new FormGroup({
        teamId: new FormControl('demo_team'),
        repoName: new FormControl('dfp-demo-repo'),
        repoPath: new FormControl('examples/dfp-demo-repo'),
        query: new FormControl('status tracking'),
        topK: new FormControl(8),
      }),
    );
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    const text = element.textContent ?? '';

    expect(text).toContain('Find code evidence');
    expect(text).toContain('What code evidence do you need?');
    expect(text).toContain('Repository settings');
    expect(text).toContain('Refresh repository memory');
    expect(text).not.toContain('Index Repo');
    expect(element.querySelector<HTMLDetailsElement>('details')?.open).toBeFalse();
  });
});
