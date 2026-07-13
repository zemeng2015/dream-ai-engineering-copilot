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
      'Turn rough requests into trusted decisions.',
    );
    expect(compiled.textContent).toContain('Approved sources only');
    expect(compiled.textContent).toContain('No automatic external writes');
    expect(compiled.textContent).toContain('What the live workflow demonstrates today');
    expect(compiled.textContent).toContain('How success will be judged');
    expect(compiled.textContent).toContain('One team | one application | one repository');
    expect(compiled.textContent).not.toContain('Qwen');
    expect(compiled.textContent).not.toContain('Alibaba');
    expect(compiled.textContent).not.toContain('+23.4');
    expect(compiled.textContent).not.toContain('35.6%');
  });

  it('links the narrative to live product workflows', () => {
    const fixture = TestBed.createComponent(LeadershipDemoComponent);
    fixture.detectChanges();
    const links = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLAnchorElement>('a'),
    ).map((link) => link.getAttribute('href'));

    expect(links).toContain('/requirements');
    expect(links).toContain('/memory');
    expect(links).toContain('/context/case-leadership-async-status');
    expect(links).toContain('/audit');
  });
});
