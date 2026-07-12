// SPDX-License-Identifier: Apache-2.0

export const V3_FPS = 30;
export const V3_DURATION = 4500;

export const v3Scenes = {
  hook: { from: 0, duration: 480 },
  thesis: { from: 480, duration: 330 },
  live_intro: { from: 810, duration: 240 },
  remember: { from: 1050, duration: 360 },
  supersede: { from: 1410, duration: 390 },
  recall: { from: 1800, duration: 360 },
  durability: { from: 2160, duration: 840 },
  benchmark: { from: 3000, duration: 600 },
  architecture: { from: 3600, duration: 510 },
  close: { from: 4110, duration: 390 },
} as const;

export type V3SceneKey = keyof typeof v3Scenes;

export const v3Captions = [
  { from: 0, to: 110, text: 'I changed a rollout from ten percent to twenty.' },
  { from: 110, to: 165, text: 'The scary part?' },
  { from: 165, to: 255, text: 'An agent can confidently bring back the old answer.' },
  { from: 255, to: 336, text: 'In production, stale truth is worse than no memory.' },
  { from: 480, to: 590, text: 'So I built DREAM.' },
  { from: 590, to: 742, text: 'Qwen understands what experience means; deterministic lifecycle rules decide what can come back.' },
  { from: 810, to: 885, text: 'This is the public build.' },
  { from: 885, to: 982, text: 'It is running in Singapore, on Alibaba Function Compute.' },
  { from: 1050, to: 1170, text: 'First, I set the canary at ten percent, for thirty minutes.' },
  { from: 1170, to: 1235, text: 'Qwen recognizes the preference.' },
  { from: 1235, to: 1307, text: 'It gives me an inspectable receipt.' },
  { from: 1410, to: 1535, text: 'Then I change it to twenty percent for forty-five minutes.' },
  { from: 1535, to: 1660, text: 'Qwen catches the conflict; DREAM keeps only the new value active.' },
  { from: 1800, to: 1945, text: 'In a fresh session, DREAM returns twenty percent in nineteen of sixty-four tokens.' },
  { from: 1945, to: 2033, text: 'The old instruction never enters context.' },
  { from: 2160, to: 2250, text: 'The test I cared about was persistence.' },
  { from: 2250, to: 2480, text: 'I saved a Qwen-curated memory, rebuilt the same source, and forced a new Function Compute instance.' },
  { from: 2480, to: 2645, text: 'The instance ID changed; the memory, decision, and Qwen receipt did not.' },
  { from: 2645, to: 2818, text: 'Twenty simultaneous conflicting writes also succeeded, leaving one active truth and nineteen historical versions.' },
  { from: 3000, to: 3260, text: 'In a clearly labeled synthetic evaluation, the same Qwen model improved from 25.3 to 48.7 across seven paired cases.' },
  { from: 3260, to: 3528, text: 'A separate twenty-four-case lifecycle suite passed every recall, stale-leak, and token-budget check.' },
  { from: 3600, to: 3745, text: 'Underneath: Angular and FastAPI on Function Compute; Qwen Cloud for meaning;' },
  { from: 3745, to: 3910, text: 'Tablestore transactions for one current truth; and temporary credentials from a narrow RAM role.' },
  { from: 4110, to: 4200, text: 'I do not want longer history.' },
  { from: 4200, to: 4303, text: 'I want one current, reviewable truth, for the next decision.' },
] as const;
