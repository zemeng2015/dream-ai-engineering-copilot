// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { LeadershipDemoComponent } from './leadership-demo.component';

describe('LeadershipDemoComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LeadershipDemoComponent],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('presents a provider-neutral governed-memory story', () => {
    const fixture = TestBed.createComponent(LeadershipDemoComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    expect(compiled.textContent).toContain(
      'Turn ambiguous requests into source-backed delivery decisions.',
    );
    expect(compiled.textContent).toContain('Approved sources only');
    expect(compiled.textContent).toContain('No automatic external writes');
    expect(compiled.textContent).toContain('Seven synthetic cases');
    expect(compiled.textContent).toContain('One team · one application · one repository');
    expect(compiled.textContent).not.toContain('Qwen');
    expect(compiled.textContent).not.toContain('Alibaba');
  });

  it('links the narrative to live product workflows', () => {
    const fixture = TestBed.createComponent(LeadershipDemoComponent);
    fixture.detectChanges();
    const links = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLAnchorElement>('a'),
    ).map((link) => link.getAttribute('href'));

    expect(links).toContain('/requirements');
    expect(links).toContain('/memory');
    expect(links).toContain('/context/case_async_status');
    expect(links).toContain('/audit');
  });
});
