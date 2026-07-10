// SPDX-License-Identifier: Apache-2.0

import {
  DREAM_PRODUCT_PROFILES,
  resolveProductProfile,
} from './product-profile';

describe('product profile', () => {
  let profileDocument: Document;
  let meta: HTMLMetaElement;

  beforeEach(() => {
    profileDocument = document.implementation.createHTMLDocument('DREAM profile test');
    meta = profileDocument.createElement('meta');
    meta.name = 'dream-product-profile';
    meta.content = 'auto';
    profileDocument.head.appendChild(meta);
  });

  it('uses the provider-neutral leadership profile by default', () => {
    expect(resolveProductProfile(profileDocument, '/mission-control')).toEqual(
      DREAM_PRODUCT_PROFILES.leadership,
    );
  });

  it('uses the competition shell for the explicit hackathon route', () => {
    expect(resolveProductProfile(profileDocument, '/hackathon-demo')).toEqual(
      DREAM_PRODUCT_PROFILES.hackathon,
    );
  });

  it('allows an explicit runtime profile override', () => {
    expect(resolveProductProfile(profileDocument, '/', 'workbench')).toEqual(
      DREAM_PRODUCT_PROFILES.workbench,
    );
  });

  it('honors an explicit build-time meta profile', () => {
    meta.content = 'hackathon';

    expect(resolveProductProfile(profileDocument, '/leadership-demo')).toEqual(
      DREAM_PRODUCT_PROFILES.hackathon,
    );
  });
});
