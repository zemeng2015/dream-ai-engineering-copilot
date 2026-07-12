// SPDX-License-Identifier: Apache-2.0

import React from 'react';
import { Composition, Still } from 'remotion';

import { DreamV3Full } from './v3/DreamV3Full';
import {
  DreamV3Thumbnail,
  GalleryV3Durability,
  GalleryV3Evidence,
  GalleryV3Hero,
  GalleryV3Live,
} from './v3/GalleryV3';
import { V3_DURATION, V3_FPS } from './v3/timeline';

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="DreamV3Full"
      component={DreamV3Full}
      durationInFrames={V3_DURATION}
      fps={V3_FPS}
      width={1920}
      height={1080}
    />
    <Still id="DreamGalleryV3Hero" component={GalleryV3Hero} width={1800} height={1200} />
    <Still id="DreamGalleryV3Live" component={GalleryV3Live} width={1800} height={1200} />
    <Still id="DreamGalleryV3Durability" component={GalleryV3Durability} width={1800} height={1200} />
    <Still id="DreamGalleryV3Evidence" component={GalleryV3Evidence} width={1800} height={1200} />
    <Still id="DreamV3Thumbnail" component={DreamV3Thumbnail} width={1280} height={720} />
  </>
);
