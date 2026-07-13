// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ImpactMapPanelComponent } from './impact-map-panel.component';

describe('ImpactMapPanelComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ImpactMapPanelComponent],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('distinguishes repository concept coverage from task impact', () => {
    const fixture = TestBed.createComponent(ImpactMapPanelComponent);
    fixture.componentRef.setInput('selectedFilePath', 'backend-api/src/StatusTracker.java');
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    const text = element.textContent ?? '';

    expect(text).toContain('Repository Concept Coverage');
    expect(text).toContain('Index diagnostic, not task impact');
    expect(text).toContain('concepts linked to the selected file');
    expect(element.querySelector<HTMLAnchorElement>('a')?.getAttribute('href')).toBe('/workbench');
  });
});
