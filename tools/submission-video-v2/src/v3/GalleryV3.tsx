// SPDX-License-Identifier: Apache-2.0

import React from 'react';
import { AbsoluteFill, Img, staticFile } from 'remotion';

import './gallery-v3.css';

const Brand: React.FC<{ inverse?: boolean }> = ({ inverse = false }) => (
  <div className={`g3-brand ${inverse ? 'inverse' : ''}`}>
    <span>D</span><strong>DREAM</strong><small>Qwen Cloud MemoryAgent</small>
  </div>
);

const Runtime: React.FC<{ inverse?: boolean }> = ({ inverse = false }) => (
  <div className={`g3-runtime ${inverse ? 'inverse' : ''}`}>
    <i /><b>LIVE</b><span>qwen3.7-plus</span><span>Tablestore</span><code>cb6255b</code>
  </div>
);

export const GalleryV3Hero: React.FC = () => (
  <AbsoluteFill className="g3-hero">
    <div className="g3-grid" />
    <Brand inverse />
    <div className="g3-hero-copy">
      <span>QWEN CLOUD / TRACK 1 MEMORYAGENT</span>
      <h1>DREAM</h1>
      <h2>AI memory should<br />know what changed.</h2>
      <p>Qwen understands the update. DREAM keeps stale truth from returning.</p>
    </div>
    <div className="g3-hero-memory">
      <section className="old"><small>REPLACED</small><strong>Use a 10% canary</strong><span>30 minutes</span><i /></section>
      <section className="current"><small>CURRENT</small><strong>Use a 20% canary</strong><span>45 minutes</span></section>
      <div><b>ONE ACTIVE TRUTH</b><span>History stays. Authority moves.</span></div>
    </div>
  </AbsoluteFill>
);

const Session: React.FC<{ image: string; label: string; color: string }> = ({ image, label, color }) => (
  <div className="g3-session" style={{ borderTopColor: color }}>
    <span style={{ color }}>{label}</span>
    <Img src={staticFile(`generated/${image}`)} />
  </div>
);

export const GalleryV3Live: React.FC = () => (
  <AbsoluteFill className="g3-paper">
    <Brand />
    <Runtime />
    <div className="g3-heading">
      <span>FRESH PUBLIC RUN / SINGAPORE FC</span>
      <h1>Three sessions. One current truth.</h1>
      <p>Every semantic decision keeps its real Qwen provider receipt.</p>
    </div>
    <div className="g3-sessions">
      <Session image="session-1.png" label="01 / REMEMBER" color="#4778d1" />
      <Session image="session-2.png" label="02 / SUPERSEDE" color="#ed6b58" />
      <Session image="session-3.png" label="03 / RECALL" color="#43b889" />
    </div>
    <div className="g3-live-facts">
      <div><strong>1</strong><span>active truth</span></div>
      <div><strong>19 / 64</strong><span>recall tokens</span></div>
      <div><strong>NO</strong><span>old value leaked</span></div>
      <div><strong>REAL</strong><span>Qwen receipts</span></div>
    </div>
  </AbsoluteFill>
);

export const GalleryV3Durability: React.FC = () => (
  <AbsoluteFill className="g3-durable">
    <div className="g3-grid" />
    <Brand inverse />
    <Runtime inverse />
    <div className="g3-durable-title">
      <span>ALIBABA CLOUD DURABILITY PROOF</span>
      <h1>The instance changed.<br /><em>The truth did not.</em></h1>
      <p>Same source. Same memory, decision, and Qwen provider receipt.</p>
    </div>
    <div className="g3-instance-row">
      <section><small>BEFORE REDEPLOY</small><strong>FC instance A</strong><code>c-6a537f3b-01459c63-95f653d85f5f</code></section>
      <div><span>same build</span><i /><code>cb6255b</code></div>
      <section className="current"><small>AFTER REDEPLOY</small><strong>FC instance B</strong><code>c-6a537fcc-01459c63-9d10c45d0864</code></section>
    </div>
    <div className="g3-ledger">
      <code>memory&nbsp;&nbsp; experience-memory-6c31f019d6da</code>
      <code>decision experience-decision-ac20b106c383</code>
      <code>Qwen&nbsp;&nbsp;&nbsp;&nbsp; f2d4a51b-3e0a-9734-ac6a-20bf45dac397</code>
    </div>
    <div className="g3-contention">
      <div><strong>20 / 20</strong><span>public writes succeeded</span></div>
      <div className="active"><strong>1</strong><span>active truth</span></div>
      <div><strong>19</strong><span>historical versions</span></div>
      <div><strong>0</strong><span>errors / 429s</span></div>
      <p>Alibaba Tablestore / partition-local transaction / temporary RAM role</p>
    </div>
  </AbsoluteFill>
);

export const GalleryV3Evidence: React.FC = () => (
  <AbsoluteFill className="g3-paper">
    <Brand />
    <Runtime />
    <div className="g3-heading evidence">
      <span>DEPLOYED AND MEASURED</span>
      <h1>Technical depth without hiding the limits.</h1>
    </div>
    <div className="g3-architecture">
      <Img src={staticFile('generated/v3/qwencloud-architecture.png')} />
    </div>
    <div className="g3-measurement">
      <span>SYNTHETIC, REPRODUCIBLE N=7</span>
      <h2>Same Qwen model.<br />Different memory.</h2>
      <div className="g3-score"><b>Stateless Qwen</b><strong>25.3</strong><i><em style={{ width: '51%' }} /></i></div>
      <div className="g3-score dream"><b>Qwen + DREAM</b><strong>48.7</strong><i><em style={{ width: '97%' }} /></i></div>
      <div className="g3-delta"><strong>+23.4</strong><span>decision score</span><b>7 / 7 wins</b></div>
      <p>Deterministic reference score / Recall@12 35.6% / not production effectiveness</p>
    </div>
  </AbsoluteFill>
);

export const DreamV3Thumbnail: React.FC = () => (
  <AbsoluteFill className="g3-thumbnail">
    <Img src={staticFile('generated/arena-final.png')} />
    <div className="g3-thumbnail-shade" />
    <Brand inverse />
    <div className="g3-thumbnail-copy">
      <span>QWEN CLOUD MEMORYAGENT</span>
      <h1>DREAM</h1>
      <h2>One current truth<br />across Qwen sessions.</h2>
      <p>Real Qwen / Function Compute / Tablestore</p>
    </div>
  </AbsoluteFill>
);
