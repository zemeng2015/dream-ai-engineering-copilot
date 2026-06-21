import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AppComponent } from './app.component';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideRouter([])],
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
    expect(app.navItems.map((item) => item.label)).toContain('Requirement Case');
    expect(app.navItems.map((item) => item.label)).toContain('Codebase Memory');
    expect(app.navItems.map((item) => item.label)).toContain('Evidence Graph');
    expect(app.navItems.map((item) => item.label)).toContain('Eval & Audit');
  });

  it('should render the DREAM shell', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('DREAM');
    expect(compiled.textContent).toContain('Mock Data Mode');
  });
});
