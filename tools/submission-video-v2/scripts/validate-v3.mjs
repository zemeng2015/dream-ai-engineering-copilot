// SPDX-License-Identifier: Apache-2.0

import { execFileSync, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(here, '..');
const repoDir = path.resolve(projectDir, '..', '..');
const generatedDir = path.join(projectDir, 'public', 'generated');
const v3Dir = path.join(generatedDir, 'v3');
const finalVideo = process.argv[2] ? path.resolve(process.argv[2]) : null;
const expectedDuration = 150;

const requireAsset = (filePath, minimumSize = 1_000) => {
  if (!fs.existsSync(filePath) || fs.statSync(filePath).size < minimumSize) {
    throw new Error(`Missing or empty asset: ${filePath}`);
  }
};

const readJson = (filePath) => JSON.parse(fs.readFileSync(filePath, 'utf8'));
const capturePath = path.join(generatedDir, 'capture-manifest.json');
const narrationPath = path.join(v3Dir, 'narration-manifest.json');

for (const file of [
  'capture-manifest.json',
  'live-click.mp4',
  'live-remember.mp4',
  'live-supersede.mp4',
  'live-recall.mp4',
  'session-1.png',
  'session-2.png',
  'session-3.png',
  'arena-final.png',
]) {
  requireAsset(path.join(generatedDir, file));
}
for (const file of ['narration-manifest.json', 'qwencloud-architecture.png']) {
  requireAsset(path.join(v3Dir, file));
}

const persistence = readJson(path.join(repoDir, 'docs', 'assets', 'qwencloud-fc-persistence-proof-summary.json'));
const contention = readJson(path.join(repoDir, 'docs', 'assets', 'qwencloud-fc-http-contention-proof-summary.json'));
const capture = readJson(capturePath);
if (
  capture.health?.provider !== 'qwen-cloud'
  || capture.health?.model !== 'qwen3.7-plus'
  || capture.health?.storageBackend !== 'tablestore'
  || capture.health?.storageDurable !== true
  || capture.health?.transactionMode !== 'partition-local-transaction'
  || !capture.health?.instanceId
  || capture.health?.buildSha !== persistence.buildSha
  || capture.health?.buildSha !== contention.buildSha
) {
  throw new Error(`Capture is not tied to the proven live runtime: ${JSON.stringify(capture.health)}`);
}
if (
  !(capture.eventSeconds?.remember < capture.eventSeconds?.supersede)
  || !(capture.eventSeconds?.supersede <= capture.eventSeconds?.recall)
) {
  throw new Error(`Live event timings are missing or out of order: ${JSON.stringify(capture.eventSeconds)}`);
}
const captureText = `${capture.runtime} ${capture.session1} ${capture.session2} ${capture.session3}`.toLowerCase();
for (const required of ['qwen', '10% canary', '20% canary', 'supersede', '19 / 64', 'old value leaked no']) {
  if (!captureText.includes(required)) throw new Error(`Live capture evidence is missing: ${required}`);
}

if (
  persistence.status !== 'pass'
  || persistence.runtimeTransition?.instanceChanged !== true
  || persistence.storage?.backend !== 'tablestore'
  || persistence.storage?.durable !== true
  || persistence.qwen?.provider !== 'qwen-cloud'
  || !persistence.qwen?.providerRequestId
) {
  throw new Error('Cross-instance Qwen persistence proof is incomplete.');
}
if (
  contention.status !== 'pass'
  || contention.requestsAttempted !== 20
  || contention.requestsSucceeded !== 20
  || contention.requestErrors.length !== 0
  || contention.activeCount !== 1
  || contention.supersededCount !== 19
) {
  throw new Error('Public HTTP contention proof no longer matches the V3 claim.');
}

const narrationSource = readJson(path.join(projectDir, 'src', 'v3', 'narration.json'));
const narration = readJson(narrationPath);
if (
  narration.model !== 'qwen3-tts-instruct-flash-2026-01-26'
  || narration.voice !== 'Ethan'
  || narration.instruction_control !== true
  || narration.optimize_instructions !== true
) {
  throw new Error(`Unexpected V3 narration configuration: ${JSON.stringify(narration)}`);
}
if (!Array.isArray(narration.segments) || narration.segments.length !== 10) {
  throw new Error('V3 narration must contain exactly ten scene clips.');
}
if (narration.total_voice_seconds < 95 || narration.total_voice_seconds > 118) {
  throw new Error(`V3 voice duration must leave meaningful breathing room: ${narration.total_voice_seconds}`);
}
if (narration.total_words < 220 || narration.total_words > 250) {
  throw new Error(`V3 script length is outside the founder-demo target: ${narration.total_words}`);
}
if (narration.total_voice_seconds / expectedDuration > 0.79) {
  throw new Error('V3 narration occupancy is too high.');
}
const sourceById = new Map(narrationSource.map((item) => [item.id, item]));
for (const segment of narration.segments) {
  const source = sourceById.get(segment.id);
  if (!source || source.text !== segment.text || source.delivery !== segment.delivery) {
    throw new Error(`Narration manifest is stale for scene: ${segment.id}`);
  }
  requireAsset(path.resolve(projectDir, segment.audio));
  if (!segment.request_id) throw new Error(`Missing Qwen TTS request ID: ${segment.id}`);
  if (segment.effective_wpm < 90 || segment.effective_wpm > 170) {
    throw new Error(`Unnatural effective pace for ${segment.id}: ${segment.effective_wpm} WPM`);
  }
}

const paired = readJson(path.join(repoDir, 'docs', 'assets', 'qwen-memory-ab-benchmark-summary.json'));
if (
  paired.case_count !== 7
  || paired.score_label !== 'deterministic_reference_score'
  || paired.baseline_mean !== 25.3
  || paired.dream_mean !== 48.7
  || paired.mean_delta !== 23.4
  || paired.dream_wins !== 7
  || paired.exact_retrieval_recall_at_12 !== 0.356
  || !paired.limitations.some((item) => item.toLowerCase().includes('synthetic'))
) {
  throw new Error('Paired benchmark evidence no longer matches the transparent V3 claim.');
}
const lifecycle = readJson(path.join(repoDir, 'docs', 'assets', 'qwen-experience-memory-benchmark-summary.json'));
if (
  lifecycle.case_count !== 24
  || lifecycle.decision_count !== 37
  || lifecycle.aggregate.passed_cases !== 24
  || lifecycle.aggregate.critical_memory_recall !== 1
  || lifecycle.aggregate.forbidden_memory_leak_rate !== 0
  || lifecycle.aggregate.token_budget_compliance !== 1
) {
  throw new Error('Lifecycle benchmark evidence no longer matches the V3 claim.');
}

const componentSource = fs.readFileSync(path.join(projectDir, 'src', 'v3', 'DreamV3Full.tsx'), 'utf8');
for (const required of [
  persistence.buildSha,
  persistence.runtimeTransition.seedInstanceId,
  persistence.runtimeTransition.verifyInstanceId,
  persistence.persistence.memoryId,
  persistence.persistence.decisionId,
  persistence.qwen.providerRequestId,
  'Recall@12 35.6%',
  '20 / 20',
]) {
  if (!componentSource.includes(required)) throw new Error(`V3 source is missing locked evidence: ${required}`);
}

const serializedEvidence = `${fs.readFileSync(capturePath, 'utf8')}\n${fs.readFileSync(narrationPath, 'utf8')}`;
for (const forbidden of [
  /DASHSCOPE_API_KEY/i,
  /Authorization\s*:/i,
  /\bLTAI[A-Za-z0-9]{12,}\b/,
  /\bsk-[A-Za-z0-9_-]{20,}\b/,
]) {
  if (forbidden.test(serializedEvidence)) throw new Error(`Potential credential leaked into V3 evidence: ${forbidden}`);
}
if (narration.credentials?.values_recorded !== false) {
  throw new Error('Narration manifest must explicitly state that credentials were not recorded.');
}

const probe = (filePath) => JSON.parse(execFileSync(
  'ffprobe',
  [
    '-v', 'error',
    '-show_entries', 'format=duration,size',
    '-show_entries', 'stream=codec_type,codec_name,width,height,sample_rate,channels',
    '-of', 'json',
    filePath,
  ],
  { encoding: 'utf8' },
));

for (const clip of ['live-remember.mp4', 'live-supersede.mp4', 'live-recall.mp4']) {
  const clipProbe = probe(path.join(generatedDir, clip));
  const duration = Number(clipProbe.format.duration);
  if (duration < 4.95 || duration > 5.05) throw new Error(`Live clip is not five seconds: ${clip} (${duration})`);
}

let final = null;
let sha256 = null;
let blackSegments = [];
let loudness = null;
let silenceGaps = [];
if (finalVideo) {
  requireAsset(finalVideo, 1_000_000);
  final = probe(finalVideo);
  const duration = Number(final.format.duration);
  if (duration < 149.9 || duration > 150.1) throw new Error(`V3 candidate must be 150 seconds: ${duration}`);
  const video = final.streams.find((stream) => stream.codec_type === 'video');
  const audio = final.streams.find((stream) => stream.codec_type === 'audio');
  if (!video || video.codec_name !== 'h264' || video.width !== 1920 || video.height !== 1080) {
    throw new Error(`V3 candidate must be 1920x1080 H.264: ${JSON.stringify(video)}`);
  }
  if (!audio || audio.codec_name !== 'aac' || audio.sample_rate !== '48000' || audio.channels !== 2) {
    throw new Error(`V3 audio must be 48 kHz stereo AAC: ${JSON.stringify(audio)}`);
  }

  const blackCheck = spawnSync(
    'ffmpeg',
    ['-hide_banner', '-i', finalVideo, '-vf', 'blackdetect=d=0.8:pix_th=0.02', '-an', '-f', 'null', 'NUL'],
    { encoding: 'utf8' },
  );
  const blackLog = `${blackCheck.stdout ?? ''}\n${blackCheck.stderr ?? ''}`;
  blackSegments = [...blackLog.matchAll(/black_duration:([0-9.]+)/g)].map((match) => Number(match[1]));
  if (blackSegments.some((durationValue) => durationValue >= 0.8)) {
    throw new Error(`V3 candidate contains a black segment: ${blackSegments.join(', ')}`);
  }

  const loudnessCheck = spawnSync(
    'ffmpeg',
    [
      '-hide_banner', '-i', finalVideo,
      '-af', 'loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json',
      '-f', 'null', 'NUL',
    ],
    { encoding: 'utf8' },
  );
  const loudnessLog = `${loudnessCheck.stdout ?? ''}\n${loudnessCheck.stderr ?? ''}`;
  const loudnessMatch = loudnessLog.match(/\{\s*"input_i"[\s\S]*?\}/);
  if (!loudnessMatch) throw new Error('Could not measure V3 candidate loudness.');
  loudness = JSON.parse(loudnessMatch[0]);
  const integratedLoudness = Number(loudness.input_i);
  const truePeak = Number(loudness.input_tp);
  if (integratedLoudness < -14.3 || integratedLoudness > -13.7 || truePeak > -0.8) {
    throw new Error(`V3 loudness is outside the delivery target: ${JSON.stringify(loudness)}`);
  }

  const silenceCheck = spawnSync(
    'ffmpeg',
    [
      '-hide_banner', '-i', finalVideo,
      '-af', 'silencedetect=noise=-38dB:d=0.7',
      '-f', 'null', 'NUL',
    ],
    { encoding: 'utf8' },
  );
  const silenceLog = `${silenceCheck.stdout ?? ''}\n${silenceCheck.stderr ?? ''}`;
  silenceGaps = [...silenceLog.matchAll(/silence_duration:\s*([0-9.]+)/g)]
    .map((match) => Number(match[1]));
  if (silenceGaps.length < 8 || Math.max(...silenceGaps) < 6) {
    throw new Error(`V3 candidate does not retain enough breathing room: ${silenceGaps.join(', ')}`);
  }
  sha256 = crypto.createHash('sha256').update(fs.readFileSync(finalVideo)).digest('hex');
}

console.log(JSON.stringify({
  ok: true,
  sourceUrl: capture.sourceUrl,
  liveRuntime: capture.health,
  narration: {
    model: narration.model,
    words: narration.total_words,
    seconds: narration.total_voice_seconds,
    occupancy: Number((narration.total_voice_seconds / expectedDuration).toFixed(4)),
  },
  proof: {
    buildSha: persistence.buildSha,
    instanceChanged: persistence.runtimeTransition.instanceChanged,
    qwenRequestId: persistence.qwen.providerRequestId,
    contention: `${contention.requestsSucceeded}/${contention.requestsAttempted}`,
  },
  final,
  blackSegments,
  loudness,
  silenceGaps,
  sha256,
}, null, 2));
