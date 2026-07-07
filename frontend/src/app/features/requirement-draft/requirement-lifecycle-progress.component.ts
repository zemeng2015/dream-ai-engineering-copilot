// SPDX-License-Identifier: Apache-2.0

import { Component, Input } from '@angular/core';

export type RequirementLifecycleState = 'idle' | 'running' | 'complete' | 'error';

export interface RequirementLifecycleStep {
  id: string;
  label: string;
  detail: string;
  runningLabel: string;
}

@Component({
  selector: 'app-requirement-lifecycle-progress',
  standalone: true,
  templateUrl: './requirement-lifecycle-progress.component.html',
  styleUrl: './requirement-lifecycle-progress.component.scss',
})
export class RequirementLifecycleProgressComponent {
  @Input() steps: RequirementLifecycleStep[] = [];
  @Input() activeIndex = -1;
  @Input() state: RequirementLifecycleState = 'idle';
  @Input() durations: Record<string, number> = {};

  stepState(index: number): 'done' | 'active' | 'pending' | 'error' {
    const step = this.steps[index];
    if (this.state === 'error' && index === this.activeIndex) {
      return 'error';
    }
    if (index === this.activeIndex && this.state === 'running') {
      return 'active';
    }
    if (this.state === 'complete' || (step && this.durations[step.id] !== undefined)) {
      return 'done';
    }
    return 'pending';
  }

  activeStep(): RequirementLifecycleStep | null {
    return this.steps[this.activeIndex] ?? null;
  }

  totalDurationLabel(): string | null {
    const duration = Object.values(this.durations).reduce((total, value) => total + value, 0);
    if (!duration) {
      return null;
    }
    if (duration < 1000) {
      return `${duration} ms`;
    }
    return `${(duration / 1000).toFixed(1)} s`;
  }
}
