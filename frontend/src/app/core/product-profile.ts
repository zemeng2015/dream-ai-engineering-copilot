// SPDX-License-Identifier: Apache-2.0

import { DOCUMENT } from '@angular/common';
import { InjectionToken, inject } from '@angular/core';

export type DreamProductProfileId = 'leadership' | 'workbench' | 'hackathon';

export interface DreamProductProfile {
  id: DreamProductProfileId;
  landingPath: string;
  shellLabel: string;
  modeLabel: string;
  modeState: string;
  environmentLabel: string;
  environmentState: string;
  showHackathonNavigation: boolean;
  generationProvider: 'config' | 'qwen-cloud';
  judgeProvider: 'none' | 'qwen-cloud';
}

declare global {
  interface Window {
    __DREAM_PRODUCT_PROFILE__?: string;
  }
}

export const DREAM_PRODUCT_PROFILES: Record<DreamProductProfileId, DreamProductProfile> = {
  leadership: {
    id: 'leadership',
    landingPath: '/leadership-demo',
    shellLabel: 'Leadership Demo',
    modeLabel: 'Governed Context',
    modeState: 'Human-Gated',
    environmentLabel: 'Deployment',
    environmentState: 'Provider Neutral',
    showHackathonNavigation: false,
    generationProvider: 'config',
    judgeProvider: 'none',
  },
  workbench: {
    id: 'workbench',
    landingPath: '/mission-control',
    shellLabel: 'Engineering Workbench',
    modeLabel: 'DREAM Core',
    modeState: 'Live Backend',
    environmentLabel: 'Environment',
    environmentState: 'Local / Private',
    showHackathonNavigation: false,
    generationProvider: 'config',
    judgeProvider: 'none',
  },
  hackathon: {
    id: 'hackathon',
    landingPath: '/hackathon-demo',
    shellLabel: 'Hackathon Demo',
    modeLabel: 'Qwen Cloud',
    modeState: 'Live Runtime',
    environmentLabel: 'Environment',
    environmentState: 'Alibaba Cloud',
    showHackathonNavigation: true,
    generationProvider: 'qwen-cloud',
    judgeProvider: 'qwen-cloud',
  },
};

export const DREAM_PRODUCT_PROFILE = new InjectionToken<DreamProductProfile>(
  'DREAM_PRODUCT_PROFILE',
  {
    providedIn: 'root',
    factory: () => resolveProductProfile(inject(DOCUMENT)),
  },
);

export function resolveProductProfile(
  documentRef: Document,
  pathname = window.location.pathname,
  runtimeProfileValue = window.__DREAM_PRODUCT_PROFILE__,
): DreamProductProfile {
  const runtimeProfile = normalizeProfile(runtimeProfileValue);
  if (runtimeProfile) {
    return DREAM_PRODUCT_PROFILES[runtimeProfile];
  }

  const configuredProfile = normalizeProfile(
    documentRef.querySelector<HTMLMetaElement>('meta[name="dream-product-profile"]')?.content,
  );
  if (configuredProfile) {
    return DREAM_PRODUCT_PROFILES[configuredProfile];
  }

  if (pathname.startsWith('/hackathon-demo')) {
    return DREAM_PRODUCT_PROFILES.hackathon;
  }
  return DREAM_PRODUCT_PROFILES.leadership;
}

function normalizeProfile(value: string | undefined): DreamProductProfileId | null {
  const normalized = value?.trim().toLowerCase();
  if (normalized === 'leadership' || normalized === 'workbench' || normalized === 'hackathon') {
    return normalized;
  }
  return null;
}
