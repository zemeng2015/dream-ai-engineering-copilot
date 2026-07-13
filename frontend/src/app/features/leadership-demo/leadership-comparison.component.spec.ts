// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';

import { LeadershipComparisonComponent } from './leadership-comparison.component';

describe('LeadershipComparisonComponent', () => {
  it('renders four accessible decision comparisons', async () => {
    await TestBed.configureTestingModule({
      imports: [LeadershipComparisonComponent],
    }).compileComponents();

    const fixture = TestBed.createComponent(LeadershipComparisonComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    expect(compiled.querySelectorAll('[role="row"]')).toHaveSize(5);
    expect(compiled.textContent).toContain('Without governed context');
    expect(compiled.textContent).toContain('With governed context');
    expect(compiled.textContent).toContain('From plausible output to reviewable decision');
    expect(compiled.querySelectorAll('.dream-cell')).toHaveSize(4);
  });
});
