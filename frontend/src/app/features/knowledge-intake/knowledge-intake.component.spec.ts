// SPDX-License-Identifier: Apache-2.0

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KnowledgeIntakeComponent } from './knowledge-intake.component';

describe('KnowledgeIntakeComponent', () => {
  let fixture: ComponentFixture<KnowledgeIntakeComponent>;
  let component: KnowledgeIntakeComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KnowledgeIntakeComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(KnowledgeIntakeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('uploads a raw source document into the review queue', async () => {
    const before = component.queue().length;
    const input = document.createElement('input');
    input.type = 'file';
    const file = new File(
      [
        '# Status Runbook\n',
        'Operators review stuck RUNNING executions and escalation notes.\n\n',
        '# Regression Tests\n',
        'Coverage should include timeout, partial success, and task progress scenarios.',
      ],
      'status-runbook.md',
      { type: 'text/markdown' },
    );
    Object.defineProperty(input, 'files', { value: [file] });

    await component.onSourceUpload({ target: input } as unknown as Event);
    fixture.detectChanges();

    const uploaded = component.selectedItem();
    expect(component.queue().length).toBe(before + 1);
    expect(uploaded?.title).toBe('Status Runbook');
    expect(uploaded?.reviewStatus).toBe('needs_review');
    expect(uploaded?.sections.length).toBeGreaterThan(1);
    expect(uploaded?.parsedConcepts).toContain('execution status');
    expect(component.uploadMessage()).toContain('parsed into');
    expect(component.selectedUploadFileName()).toBe('status-runbook.md');
  });

  it('records review comments through approve and promote actions', async () => {
    const input = document.createElement('input');
    input.type = 'file';
    const file = new File(['# API Contract\nStatus endpoint payload needs approval.'], 'api-contract-hld.md');
    Object.defineProperty(input, 'files', { value: [file] });
    await component.onSourceUpload({ target: input } as unknown as Event);

    component.reviewComment.set('Approved after checking the task status contract.');
    component.approveSelected();
    expect(component.selectedItem()?.reviewStatus).toBe('approved');
    expect(component.selectedItem()?.reviewNotes[0]).toContain('Approved after checking');

    component.reviewComment.set('Promote into architecture pack for retrieval demo.');
    component.promoteSelected();
    expect(component.selectedItem()?.reviewStatus).toBe('promoted');
    expect(component.selectedItem()?.queueStatus).toBe('promoted');
    expect(component.selectedItem()?.reviewNotes[0]).toContain('Promote into architecture pack');
  });

  it('renders an English-only custom upload control', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const localizedChooseFile = '\u9009\u62e9\u6587\u4ef6';
    const localizedNoFileSelected = '\u672a\u9009\u62e9\u4efb\u4f55\u6587\u4ef6';

    expect(compiled.textContent).toContain('Choose source file');
    expect(compiled.textContent).toContain('No file selected');
    expect(compiled.textContent).not.toContain(localizedChooseFile);
    expect(compiled.textContent).not.toContain(localizedNoFileSelected);
  });
});
