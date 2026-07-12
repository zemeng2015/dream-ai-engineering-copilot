// SPDX-License-Identifier: Apache-2.0

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(here, '..');
const generatedDir = path.join(projectDir, 'public', 'generated');
const baseUrl = process.argv[2] ?? 'https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run';
const chromeCandidates = [
  process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean);
const executablePath = chromeCandidates.find((candidate) => fs.existsSync(candidate));

if (!executablePath) {
  throw new Error('Chrome or Edge was not found. Set CHROME_PATH and retry.');
}

fs.mkdirSync(generatedDir, { recursive: true });

const healthResponse = await fetch(`${baseUrl.replace(/\/$/, '')}/health`);
if (!healthResponse.ok) {
  throw new Error(`Live health check failed with HTTP ${healthResponse.status}.`);
}
const health = await healthResponse.json();
if (
  health.llm_provider !== 'qwen-cloud'
  || health.llm_api_key_configured !== true
  || health.experience_storage_backend !== 'tablestore'
  || health.experience_storage_durable !== true
  || health.experience_transaction_mode !== 'partition-local-transaction'
  || !health.runtime_instance_id
  || !health.build_sha
) {
  throw new Error(`Live runtime evidence is incomplete: ${JSON.stringify(health)}`);
}

const proxy = http.createServer(async (request, response) => {
  try {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    const requestBody = Buffer.concat(chunks);
    const upstreamUrl = new URL(request.url ?? '/', baseUrl);
    const headers = { ...request.headers };
    delete headers.host;
    delete headers['content-length'];

    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers,
      body: requestBody.length > 0 ? requestBody : undefined,
      redirect: 'manual',
    });
    const blockedHeaders = new Set([
      'connection',
      'content-disposition',
      'content-encoding',
      'content-length',
      'transfer-encoding',
    ]);
    for (const [name, value] of upstream.headers.entries()) {
      if (!blockedHeaders.has(name.toLowerCase())) response.setHeader(name, value);
    }
    response.statusCode = upstream.status;
    response.end(Buffer.from(await upstream.arrayBuffer()));
  } catch (error) {
    response.statusCode = 502;
    response.end(`Capture proxy error: ${error instanceof Error ? error.message : String(error)}`);
  }
});

await new Promise((resolve, reject) => {
  proxy.once('error', reject);
  proxy.listen(0, '127.0.0.1', resolve);
});
const address = proxy.address();
if (!address || typeof address === 'string') throw new Error('Capture proxy did not bind a TCP port.');
const captureBaseUrl = `http://127.0.0.1:${address.port}`;

const browser = await chromium.launch({
  executablePath,
  headless: true,
  args: ['--disable-features=MediaRouter', '--hide-scrollbars'],
});

const recordStart = Date.now();
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 2,
  recordVideo: { dir: generatedDir, size: { width: 1920, height: 1080 } },
});
const page = await context.newPage();

await page.addInitScript((apiBaseUrl) => {
  window.__DREAM_API_BASE_URL__ = apiBaseUrl;
  document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = `
      * { cursor: none !important; }
      #dream-demo-cursor {
        position: fixed; left: 0; top: 0; z-index: 2147483647;
        width: 24px; height: 24px; border: 3px solid #ffffff;
        border-radius: 50%; background: #0fa679; pointer-events: none;
        box-shadow: 0 3px 14px rgba(0,0,0,.38);
        transform: translate(-50%, -50%); transition: width .12s, height .12s;
      }
      #dream-demo-cursor[data-down="true"] { width: 38px; height: 38px; }
    `;
    document.head.appendChild(style);
    const cursor = document.createElement('div');
    cursor.id = 'dream-demo-cursor';
    document.body.appendChild(cursor);
    document.addEventListener('mousemove', (event) => {
      cursor.style.left = `${event.clientX}px`;
      cursor.style.top = `${event.clientY}px`;
    });
    document.addEventListener('mousedown', () => cursor.dataset.down = 'true');
    document.addEventListener('mouseup', () => cursor.dataset.down = 'false');
  });
}, captureBaseUrl);

const sourceUrl = `${baseUrl.replace(/\/$/, '')}/hackathon-demo`;
const pageUrl = `${captureBaseUrl}/hackathon-demo`;
await page.goto(pageUrl, { waitUntil: 'networkidle', timeout: 60_000 });
await page.locator('.run-button').waitFor({ state: 'visible', timeout: 30_000 });
await page.locator('.runtime-state').waitFor({ state: 'visible', timeout: 30_000 });

const runtimeText = (await page.locator('.runtime-state').innerText()).trim();
if (!runtimeText.toLowerCase().includes('qwen')) {
  throw new Error(`Live Qwen runtime was not ready: ${runtimeText}`);
}

await page.screenshot({ path: path.join(generatedDir, 'ready.png') });

const button = page.locator('.run-button');
const box = await button.boundingBox();
if (!box) throw new Error('Run button has no visible bounding box.');

await page.mouse.move(360, 160);
await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 34 });
await page.waitForTimeout(550);
const clickSeconds = (Date.now() - recordStart) / 1000;
await button.click();
await page.waitForTimeout(700);
await page.screenshot({ path: path.join(generatedDir, 'running.png') });

const firstCard = page.locator('.session-card').nth(0);
const secondCard = page.locator('.session-card').nth(1);
const recallCard = page.locator('.session-card').nth(2);

await firstCard.locator('em').filter({ hasText: 'remember' }).waitFor({ state: 'visible', timeout: 90_000 });
const session1Seconds = (Date.now() - recordStart) / 1000;
await firstCard.screenshot({ path: path.join(generatedDir, 'session-1.png') });

await secondCard.locator('em').filter({ hasText: 'supersede' }).waitFor({ state: 'visible', timeout: 90_000 });
const session2Seconds = (Date.now() - recordStart) / 1000;
await secondCard.screenshot({ path: path.join(generatedDir, 'session-2.png') });

await page.locator('.lifecycle-proof').waitFor({ state: 'visible', timeout: 90_000 });
const session3Seconds = (Date.now() - recordStart) / 1000;
await recallCard.screenshot({ path: path.join(generatedDir, 'session-3.png') });
await page.locator('.judge-arena').screenshot({ path: path.join(generatedDir, 'arena-final.png') });

const captureEvidence = {
  capturedAt: new Date().toISOString(),
  sourceUrl,
  runtime: runtimeText,
  health: {
    deploymentTarget: health.deployment_target,
    region: health.alibaba_cloud_region,
    service: health.alibaba_cloud_service,
    provider: health.llm_provider,
    model: health.llm_model,
    storageBackend: health.experience_storage_backend,
    storageDurable: health.experience_storage_durable,
    transactionMode: health.experience_transaction_mode,
    instanceId: health.runtime_instance_id,
    buildSha: health.build_sha,
  },
  session1: (await firstCard.innerText()).replace(/\s+/g, ' ').trim(),
  session2: (await secondCard.innerText()).replace(/\s+/g, ' ').trim(),
  session3: (await recallCard.innerText()).replace(/\s+/g, ' ').trim(),
  clickSeconds,
  eventSeconds: {
    remember: session1Seconds,
    supersede: session2Seconds,
    recall: session3Seconds,
  },
};

const rawVideo = page.video();
await context.close();

if (!rawVideo) throw new Error('Playwright did not produce a capture video.');
const rawVideoPath = path.join(generatedDir, 'live-run.webm');
await rawVideo.saveAs(rawVideoPath);
await browser.close();
await new Promise((resolve, reject) => proxy.close((error) => error ? reject(error) : resolve()));

for (const file of fs.readdirSync(generatedDir)) {
  if (file.startsWith('page@') && file.endsWith('.webm')) {
    fs.rmSync(path.join(generatedDir, file), { force: true });
  }
}

const clipStart = Math.max(0, clickSeconds - 1.4);
execFileSync(
  'ffmpeg',
  [
    '-hide_banner', '-loglevel', 'error', '-y',
    '-ss', clipStart.toFixed(3), '-i', rawVideoPath,
    '-t', '5.0', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    path.join(generatedDir, 'live-click.mp4'),
  ],
  { stdio: 'inherit' },
);

for (const [name, eventSeconds] of Object.entries({
  remember: session1Seconds,
  supersede: session2Seconds,
  recall: session3Seconds,
})) {
  const eventClipStart = Math.max(0, eventSeconds - 3.4);
  execFileSync(
    'ffmpeg',
    [
      '-hide_banner', '-loglevel', 'error', '-y',
      '-ss', eventClipStart.toFixed(3), '-i', rawVideoPath,
      '-vf', 'tpad=stop_mode=clone:stop_duration=5',
      '-t', '5.0', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
      '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
      path.join(generatedDir, `live-${name}.mp4`),
    ],
    { stdio: 'inherit' },
  );
}

fs.writeFileSync(
  path.join(generatedDir, 'capture-manifest.json'),
  `${JSON.stringify(captureEvidence, null, 2)}\n`,
  'utf8',
);

console.log(JSON.stringify({
  ok: true,
  sourceUrl,
  runtime: runtimeText,
  clickSeconds,
  generatedDir,
}, null, 2));
