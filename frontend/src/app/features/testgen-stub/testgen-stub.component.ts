import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { TestGenStubPlan, TestGenStubResult } from '../../core/dream-models';
import { MockDreamService } from '../../core/mock-dream.service';

@Component({
  selector: 'app-testgen-stub',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './testgen-stub.component.html',
})
export class TestgenStubComponent {
  private readonly dream = inject(MockDreamService);
  private readonly fb = inject(FormBuilder);

  readonly plan = signal<TestGenStubPlan | null>(null);
  readonly result = signal<TestGenStubResult | null>(null);

  readonly form = this.fb.nonNullable.group({
    teamId: ['demo_team', Validators.required],
    repoPath: ['examples/dfp-demo-repo', Validators.required],
    targetLanguage: ['java', Validators.required],
    dryRun: true,
  });

  createPlan(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.plan.set(this.dream.planTestGenStub(this.form.getRawValue()));
  }

  runStub(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.result.set(this.dream.runTestGenStub(this.form.getRawValue()));
  }
}
