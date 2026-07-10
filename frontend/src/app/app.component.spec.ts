// SPDX-License-Identifier: Apache-2.0

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AppComponent } from './app.component';
import {
  DREAM_PRODUCT_PROFILE,
  DREAM_PRODUCT_PROFILES,
} from './core/product-profile';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideRouter([]),
        {
          provide: DREAM_PRODUCT_PROFILE,
          useValue: DREAM_PRODUCT_PROFILES.leadership,
        },
      ],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should expose primary navigation items', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app.navItems.map((item) => item.label)).toEqual([
      'Leadership Demo',
      'Mission Control',
      'Memory Hub',
      'Engineering Workbench',
      'Codebase Index',
      'Audit & Eval',
    ]);
  });

  it('should render the DREAM shell', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('DREAM');
    expect(compiled.textContent).toContain('Human-Gated');
    expect(compiled.textContent).toContain('Provider Neutral');
    expect(compiled.textContent).not.toContain('Alibaba Cloud');
  });
});
