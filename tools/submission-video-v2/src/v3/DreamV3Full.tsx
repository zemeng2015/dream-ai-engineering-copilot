// SPDX-License-Identifier: Apache-2.0

import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

import { V3SceneKey, v3Captions, v3Scenes } from './timeline';
import './v3.css';

const colors = {
  night: '#071820',
  ink: '#0f2f3a',
  paper: '#f4f7f6',
  white: '#ffffff',
  mint: '#43b889',
  paleMint: '#dff3ea',
  coral: '#ed6b58',
  gold: '#e4ad3d',
  blue: '#4778d1',
  muted: '#678087',
};

const proof = {
  build: 'cb6255b7a1565a631daec6215bd146f495d97df8',
  seedInstance: 'c-6a537f3b-01459c63-95f653d85f5f',
  verifyInstance: 'c-6a537fcc-01459c63-9d10c45d0864',
  memory: 'experience-memory-6c31f019d6da',
  decision: 'experience-decision-ac20b106c383',
  request: 'f2d4a51b-3e0a-9734-ac6a-20bf45dac397',
};

const Brand: React.FC<{ inverse?: boolean }> = ({ inverse = false }) => (
  <div className={`v3-brand ${inverse ? 'inverse' : ''}`}>
    <span>D</span>
    <strong>DREAM</strong>
    <small>Qwen Cloud MemoryAgent</small>
  </div>
);

const RuntimeProof: React.FC<{ dark?: boolean }> = ({ dark = false }) => (
  <div className={`v3-runtime ${dark ? 'dark' : ''}`}>
    <i />
    <span>LIVE</span>
    <b>qwen3.7-plus</b>
    <b>Tablestore</b>
    <code>{proof.build.slice(0, 7)}</code>
  </div>
);

const SceneAudio: React.FC<{ id: V3SceneKey }> = ({ id }) => (
  <Audio src={staticFile(`generated/v3/${id}-mastered.wav`)} />
);

const CaptionTrack: React.FC = () => {
  const frame = useCurrentFrame();
  const active = v3Captions.find((caption) => frame >= caption.from && frame < caption.to);
  if (!active) return null;
  const opacity = interpolate(
    frame,
    [active.from, active.from + 5, active.to - 5, active.to],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );
  return <div className="v3-caption" style={{ opacity }}>{active.text}</div>;
};

const SceneFade: React.FC<React.PropsWithChildren> = ({ children }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 9], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};

const HookScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const oldEnter = spring({ frame: frame - 25, fps, config: { damping: 18, stiffness: 90 } });
  const newEnter = spring({ frame: frame - 105, fps, config: { damping: 18, stiffness: 90 } });
  const wrongEnter = spring({ frame: frame - 230, fps, config: { damping: 20, stiffness: 85 } });
  const strike = interpolate(frame, [310, 360], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  return (
    <SceneFade>
      <AbsoluteFill className="v3-hook">
        <div className="v3-grid" />
        <Brand inverse />
        <div className="v3-hook-heading">
          <span>A SMALL MEMORY FAILURE</span>
          <h1>It remembered.<br /><em>It was wrong.</em></h1>
        </div>
        <div className="v3-conversation">
          <div className="v3-message old" style={{ opacity: oldEnter, transform: `translateY(${(1 - oldEnter) * 35}px)` }}>
            <small>Yesterday</small><strong>Use a 10% canary.</strong><span>30 minutes</span>
          </div>
          <div className="v3-thread-line" />
          <div className="v3-message current" style={{ opacity: newEnter, transform: `translateY(${(1 - newEnter) * 35}px)` }}>
            <small>Today / replaced</small><strong>Use a 20% canary.</strong><span>45 minutes</span>
          </div>
          <div className="v3-wrong-answer" style={{ opacity: wrongEnter }}>
            <small>AGENT RECALL</small>
            <strong>Use the 10% canary.</strong>
            <i style={{ transform: `scaleX(${strike})` }} />
          </div>
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};

const ThesisScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const qwen = spring({ frame: frame - 35, fps, config: { damping: 18, stiffness: 95 } });
  const dream = spring({ frame: frame - 125, fps, config: { damping: 18, stiffness: 95 } });
  return (
    <SceneFade>
      <AbsoluteFill className="v3-thesis">
        <Brand />
        <div className="v3-section-title">
          <span>THE IDEA</span>
          <h2>Meaning can change.<br />Truth needs a lifecycle.</h2>
        </div>
        <div className="v3-role qwen" style={{ opacity: qwen, transform: `translateX(${(1 - qwen) * 45}px)` }}>
          <small>QWEN</small>
          <strong>Understands the update</strong>
          <div>remember&nbsp;&nbsp; supersede&nbsp;&nbsp; forget&nbsp;&nbsp; ignore</div>
        </div>
        <div className="v3-role-connector">-&gt;</div>
        <div className="v3-role dream" style={{ opacity: dream, transform: `translateX(${(1 - dream) * 45}px)` }}>
          <small>DREAM</small>
          <strong>Makes stale truth ineligible</strong>
          <div>state&nbsp;&nbsp; provenance&nbsp;&nbsp; expiry&nbsp;&nbsp; budget</div>
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};

const LiveScene: React.FC = () => {
  const frame = useCurrentFrame();
  const videoOpacity = interpolate(frame, [0, 10, 165, 195], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const zoom = interpolate(frame, [0, 230], [1.01, 1.055], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.ease),
  });
  return (
    <SceneFade>
      <AbsoluteFill className="v3-live">
        <div className="v3-live-media" style={{ transform: `scale(${zoom})` }}>
          <Img src={staticFile('generated/arena-final.png')} />
          <OffthreadVideo src={staticFile('generated/live-click.mp4')} muted style={{ opacity: videoOpacity }} />
        </div>
        <div className="v3-live-shade" />
        <Brand inverse />
        <RuntimeProof dark />
        <div className="v3-live-copy">
          <span>PUBLIC DEPLOYMENT / SINGAPORE</span>
          <h2>No mock responses.<br />Let us run it.</h2>
          <code>dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run</code>
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};

type GuidedProofProps = {
  image: string;
  video: string;
  step: string;
  eyebrow: string;
  title: string;
  body: string;
  accent: string;
  facts: Array<[string, string]>;
};

const GuidedProof: React.FC<GuidedProofProps> = ({ image, video, step, eyebrow, title, body, accent, facts }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const media = spring({ frame: frame - 15, fps, config: { damping: 20, stiffness: 82 } });
  const zoom = interpolate(frame, [0, 350], [1.015, 1.06], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.ease),
  });
  const videoOpacity = interpolate(frame, [0, 8, 135, 165], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  return (
    <SceneFade>
      <AbsoluteFill className="v3-guided">
        <Brand />
        <RuntimeProof />
        <div className="v3-guided-copy">
          <span style={{ color: accent }}>{step}</span>
          <small>{eyebrow}</small>
          <h2>{title}</h2>
          <p>{body}</p>
          <div className="v3-facts">
            {facts.map(([label, value], index) => {
              const enter = spring({ frame: frame - 115 - index * 35, fps, config: { damping: 18 } });
              return <div key={label} style={{ opacity: enter, borderColor: accent }}><b>{value}</b><span>{label}</span></div>;
            })}
          </div>
        </div>
        <div className="v3-proof-media" style={{ opacity: media, transform: `translateX(${(1 - media) * 60}px) scale(${zoom})` }}>
          <Img src={staticFile(`generated/${image}`)} />
          <OffthreadVideo src={staticFile(`generated/${video}`)} muted style={{ opacity: videoOpacity }} />
          <div className="v3-proof-motion-label" style={{ opacity: videoOpacity }}><i /> CONTINUOUS LIVE RUN</div>
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};

const PersistenceProof: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const persistenceOpacity = interpolate(frame, [0, 22, 430, 500], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const burstOpacity = interpolate(frame, [465, 530, 825], [0, 1, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const connector = interpolate(frame, [105, 245], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  return (
    <SceneFade>
      <AbsoluteFill className="v3-durability">
        <div className="v3-grid" />
        <Brand inverse />
        <RuntimeProof dark />
        <div className="v3-durable-phase" style={{ opacity: persistenceOpacity }}>
          <div className="v3-durable-heading">
            <span>THE TEST I CARED ABOUT</span>
            <h2>I did not trust<br />process-local memory.</h2>
          </div>
          <div className="v3-instance-flow">
            <div className="v3-instance">
              <small>BEFORE REDEPLOY</small><strong>FC instance A</strong><code>{proof.seedInstance}</code>
            </div>
            <div className="v3-redeploy"><i style={{ transform: `scaleX(${connector})` }} /><span>same source<br /><code>{proof.build.slice(0, 7)}</code></span></div>
            <div className="v3-instance current">
              <small>AFTER REDEPLOY</small><strong>FC instance B</strong><code>{proof.verifyInstance}</code>
            </div>
          </div>
          <div className="v3-unchanged">
            <span>CHANGED</span><strong>instance ID</strong>
            <span>UNCHANGED</span><strong>memory + decision + Qwen receipt</strong>
          </div>
          <div className="v3-proof-ledger">
            <code>{proof.memory}</code><code>{proof.decision}</code><code>Qwen {proof.request}</code>
          </div>
        </div>
        <div className="v3-burst-phase" style={{ opacity: burstOpacity }}>
          <div className="v3-durable-heading">
            <span>REAL PUBLIC HTTP CONTENTION</span>
            <h2>Then I tried to break<br />the single truth.</h2>
          </div>
          <div className="v3-request-cloud">
            {Array.from({ length: 20 }, (_, index) => {
              const enter = spring({ frame: frame - 495 - index * 5, fps, config: { damping: 18, stiffness: 115 } });
              return <i key={index} style={{ opacity: enter, transform: `scaleX(${enter})` }} />;
            })}
          </div>
          <div className="v3-burst-arrow">20 conflicting writes -&gt;</div>
          <div className="v3-burst-result">
            <div><strong>20 / 20</strong><span>succeeded</span></div>
            <div className="active"><strong>1</strong><span>active truth</span></div>
            <div><strong>19</strong><span>historical</span></div>
            <div><strong>0</strong><span>errors / 429s</span></div>
          </div>
          <div className="v3-burst-note">Alibaba Tablestore partition-local transaction / 7.494 seconds</div>
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};

const BenchmarkScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pairedOpacity = interpolate(frame, [0, 20, 305, 365], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const lifecycleOpacity = interpolate(frame, [325, 385, 590], [0, 1, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const baseline = interpolate(frame, [80, 190], [0, 50.6], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const dream = interpolate(frame, [115, 230], [0, 97.4], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const checks = [
    ['100%', 'critical recall'],
    ['0%', 'stale-memory leak'],
    ['100%', 'token-budget compliance'],
  ];
  return (
    <SceneFade>
      <AbsoluteFill className="v3-benchmark">
        <Brand />
        <RuntimeProof />
        <div className="v3-benchmark-heading">
          <span>SYNTHETIC, REPRODUCIBLE CASES</span>
          <h2>I measured the decision,<br />not just the storage.</h2>
        </div>
        <div className="v3-paired" style={{ opacity: pairedOpacity }}>
          <div className="v3-bar-row"><b>Stateless Qwen</b><strong>25.3</strong><i><em style={{ width: `${baseline}%` }} /></i></div>
          <div className="v3-bar-row dream"><b>Qwen + DREAM</b><strong>48.7</strong><i><em style={{ width: `${dream}%` }} /></i></div>
          <div className="v3-lift"><strong>+23.4</strong><span>decision-score lift</span><b>7 / 7 paired wins</b></div>
          <small>Same qwen3.7-plus / synthetic n=7 / deterministic reference score / Recall@12 35.6%</small>
        </div>
        <div className="v3-lifecycle" style={{ opacity: lifecycleOpacity }}>
          <strong>24 / 24</strong><span>lifecycle cases passed</span>
          <div>
            {checks.map(([value, label], index) => {
              const enter = spring({ frame: frame - 370 - index * 24, fps, config: { damping: 18 } });
              return <section key={label} style={{ opacity: enter }}><b>{value}</b><small>{label}</small></section>;
            })}
          </div>
          <p>37 real Qwen curator decisions inside the controlled lifecycle suite</p>
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};

const ArchitectureScene: React.FC = () => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [15, 75], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const zoom = interpolate(frame, [0, 500], [1, 1.035], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.ease),
  });
  return (
    <SceneFade>
      <AbsoluteFill className="v3-architecture">
        <Brand />
        <RuntimeProof />
        <div className="v3-architecture-heading">
          <span>WHAT HAPPENS WHEN NOBODY IS WATCHING</span>
          <h2>The safety is in the stack.</h2>
        </div>
        <div className="v3-architecture-image" style={{ opacity: enter, transform: `scale(${zoom})` }}>
          <Img src={staticFile('generated/v3/qwencloud-architecture.png')} />
        </div>
        <div className="v3-architecture-foot">
          <b>Qwen makes the semantic call</b><i />
          <b>Tablestore commits lifecycle state</b><i />
          <b>Function Compute exposes proof</b>
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};

const CloseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame: frame - 10, fps, config: { damping: 20, stiffness: 75 } });
  const proofs = ['REAL QWEN RECEIPTS', 'DURABLE TABLESTORE', 'PUBLIC FC BUILD'];
  return (
    <SceneFade>
      <AbsoluteFill className="v3-close">
        <div className="v3-grid" />
        <Brand inverse />
        <div className="v3-close-main" style={{ opacity: enter, transform: `translateY(${(1 - enter) * 25}px)` }}>
          <span>DREAM</span>
          <h1>One current,<br /><em>reviewable truth.</em></h1>
          <p>For the next decision.</p>
        </div>
        <div className="v3-close-proof">
          {proofs.map((item, index) => {
            const proofEnter = spring({ frame: frame - 130 - index * 28, fps, config: { damping: 18 } });
            return <div key={item} style={{ opacity: proofEnter }}><i />{item}</div>;
          })}
        </div>
        <code className="v3-close-url">dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/hackathon-demo</code>
      </AbsoluteFill>
    </SceneFade>
  );
};

const Scene: React.FC<React.PropsWithChildren<{ id: V3SceneKey }>> = ({ id, children }) => {
  const scene = v3Scenes[id];
  return (
    <Sequence from={scene.from} durationInFrames={scene.duration}>
      <SceneAudio id={id} />
      {children}
    </Sequence>
  );
};

export const DreamV3Full: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: colors.night }}>
    <Scene id="hook"><HookScene /></Scene>
    <Scene id="thesis"><ThesisScene /></Scene>
    <Scene id="live_intro"><LiveScene /></Scene>
    <Scene id="remember">
      <GuidedProof
        image="session-1.png"
        video="live-remember.mp4"
        step="SESSION 1"
        eyebrow="I GIVE IT A PREFERENCE"
        title="Qwen understands what should persist."
        body="A concrete deployment choice becomes cross-session experience, with the model receipt still visible."
        accent={colors.blue}
        facts={[["CURRENT TRUTH", "10% / 30 min"], ["QWEN ACTION", "remember"]]}
      />
    </Scene>
    <Scene id="supersede">
      <GuidedProof
        image="session-2.png"
        video="live-supersede.mp4"
        step="SESSION 2"
        eyebrow="THEN I CHANGE MY MIND"
        title="History stays. Authority moves."
        body="Qwen catches the semantic conflict. DREAM makes the replaced instruction ineligible for recall."
        accent={colors.coral}
        facts={[["NEW TRUTH", "20% / 45 min"], ["ACTIVE COUNT", "exactly 1"]]}
      />
    </Scene>
    <Scene id="recall">
      <GuidedProof
        image="session-3.png"
        video="live-recall.mp4"
        step="SESSION 3"
        eyebrow="A FRESH SESSION ASKS WHAT IS TRUE NOW"
        title="Only the current answer returns."
        body="The recall budget is hard, and the obsolete instruction never reaches the model context."
        accent={colors.mint}
        facts={[["BUDGET USED", "19 / 64"], ["OLD VALUE LEAK", "no"]]}
      />
    </Scene>
    <Scene id="durability"><PersistenceProof /></Scene>
    <Scene id="benchmark"><BenchmarkScene /></Scene>
    <Scene id="architecture"><ArchitectureScene /></Scene>
    <Scene id="close"><CloseScene /></Scene>
    <CaptionTrack />
  </AbsoluteFill>
);
