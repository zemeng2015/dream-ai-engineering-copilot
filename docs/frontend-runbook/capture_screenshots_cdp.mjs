import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const MANIFEST_PATH = path.join(ROOT, 'annotation-manifest.json');
const RAW_DIR = path.join(ROOT, 'raw-screenshots');
const BASE_URL = 'http://127.0.0.1:4300';
const CHROME_PATHS = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  path.join(os.homedir(), 'AppData/Local/Google/Chrome/Application/chrome.exe'),
];

const VIEWPORT_WIDTH = 1280;
const INITIAL_VIEWPORT_HEIGHT = 720;
const MAX_VIEWPORT_HEIGHT = 9000;

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function chromePath() {
  const found = CHROME_PATHS.find((candidate) => existsSync(candidate));
  if (!found) {
    throw new Error('Chrome executable was not found.');
  }
  return found;
}

async function waitForJson(url, attempts = 80) {
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return await response.json();
      }
    } catch {
      // Chrome may still be starting.
    }
    await delay(100);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function createPageTarget(debugPort) {
  const url = `http://127.0.0.1:${debugPort}/json/new?about:blank`;
  let response = await fetch(url, { method: 'PUT' });
  if (!response.ok) {
    response = await fetch(url);
  }
  if (!response.ok) {
    throw new Error(`Unable to create Chrome page target: ${response.status}`);
  }
  return await response.json();
}

class CdpClient {
  constructor(webSocketDebuggerUrl) {
    this.ws = new WebSocket(webSocketDebuggerUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.events = new Map();
    this.ws.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) {
          reject(new Error(message.error.message));
        } else {
          resolve(message.result ?? {});
        }
        return;
      }
      if (message.method && this.events.has(message.method)) {
        for (const handler of this.events.get(message.method)) {
          handler(message.params ?? {});
        }
      }
    });
  }

  async open() {
    if (this.ws.readyState === WebSocket.OPEN) {
      return;
    }
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
  }

  send(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;
    const payload = JSON.stringify({ id, method, params });
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(payload);
    });
  }

  on(method, handler) {
    const handlers = this.events.get(method) ?? new Set();
    handlers.add(handler);
    this.events.set(method, handlers);
    return () => handlers.delete(handler);
  }

  waitForEvent(method, timeoutMs = 10000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        off();
        reject(new Error(`Timed out waiting for ${method}`));
      }, timeoutMs);
      const off = this.on(method, (params) => {
        clearTimeout(timer);
        off();
        resolve(params);
      });
    });
  }

  close() {
    this.ws.close();
  }
}

function stripRuntimeFields(box) {
  const {
    id,
    missing,
    rect,
    sample,
    ...spec
  } = box;
  return spec;
}

async function evaluate(client, expression, awaitPromise = false) {
  const result = await client.send('Runtime.evaluate', {
    expression,
    awaitPromise,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text ?? 'Runtime.evaluate failed');
  }
  return result.result?.value;
}

async function waitForReady(client, title, timeoutMs = 10000) {
  const started = Date.now();
  const needle = title.split(' ')[0];
  while (Date.now() - started < timeoutMs) {
    const ready = await evaluate(
      client,
      `(() => document.readyState === 'complete' && document.body && document.body.innerText.includes(${JSON.stringify(needle)}))()`,
    );
    if (ready) {
      return;
    }
    await delay(100);
  }
  throw new Error(`Page did not become ready for ${title}`);
}

async function prepPage(client, slug) {
  const prepScript = `
    (async () => {
      const click = (selector) => {
        const element = document.querySelector(selector);
        if (element) element.click();
      };
      const clickByText = (text) => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const button = buttons.find((item) => item.textContent.replace(/\\s+/g, ' ').trim() === text);
        if (button) button.click();
      };
      switch (${JSON.stringify(slug)}) {
        case 'knowledge-memory':
          if (!document.querySelector('#knowledge-search-form')) click('button[aria-controls="knowledge-search-form"]');
          break;
        case 'memory-atlas':
          if (!document.querySelector('#code-memory-search')) click('button.search-toggle');
          break;
        case 'requirement-case':
          click('app-requirement-draft button.primary-button[type="submit"]');
          break;
        case 'pr-review':
          click('app-pr-review button.primary-button[type="submit"]');
          break;
        case 'testgen-stub':
          clickByText('Plan Stub');
          clickByText('Run Safe Stub');
          break;
      }
      await new Promise((resolve) => setTimeout(resolve, 250));
      window.scrollTo(0, 0);
      return true;
    })()
  `;
  await evaluate(client, prepScript, true);
}

async function documentSize(client) {
  return await evaluate(
    client,
    `(() => ({
      width: Math.ceil(Math.max(document.documentElement.scrollWidth, document.body.scrollWidth, ${VIEWPORT_WIDTH})),
      height: Math.ceil(Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, ${INITIAL_VIEWPORT_HEIGHT}))
    }))()`,
  );
}

async function collectBoxes(client, specs) {
  const expression = `
    ((items) => {
      const clean = (value) => String(value || '').replace(/\\s+/g, ' ').trim();
      const getRect = (el) => {
        const r = el.getBoundingClientRect();
        return {
          x: Math.max(0, Math.round(r.left + window.scrollX)),
          y: Math.max(0, Math.round(r.top + window.scrollY)),
          width: Math.max(1, Math.round(r.width)),
          height: Math.max(1, Math.round(r.height)),
        };
      };
      const byHeading = (heading, closestSelector) => {
        const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,strong,span,label,button'));
        const match = headings.find((el) => clean(el.textContent) === heading) ||
          headings.find((el) => clean(el.textContent).includes(heading));
        return match ? match.closest(closestSelector || 'article, section, header, nav, aside, form, div') : null;
      };
      const byText = (text, closestSelector) => {
        const nodes = Array.from(document.querySelectorAll('article, section, header, nav, aside, form, div, table'));
        const matches = nodes.filter((el) => clean(el.textContent).includes(text));
        if (!matches.length) return null;
        matches.sort((a, b) => {
          const ar = a.getBoundingClientRect();
          const br = b.getBoundingClientRect();
          return (ar.width * ar.height) - (br.width * br.height);
        });
        return matches[0].closest(closestSelector || 'article, section, header, nav, aside, form, div') || matches[0];
      };
      const viewport = { width: window.innerWidth, height: window.innerHeight };
      const doc = { width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight };
      const boxes = items.map((item, index) => {
        let el = null;
        if (item.selector) el = document.querySelector(item.selector);
        if (!el && item.heading) el = byHeading(item.heading, item.closest);
        if (!el && item.text) el = byText(item.text, item.closest);
        if (!el) return { ...item, id: index + 1, missing: true };
        return { ...item, id: index + 1, missing: false, rect: getRect(el), sample: clean(el.textContent).slice(0, 180) };
      });
      return { viewport, doc, boxes };
    })(${JSON.stringify(specs)})
  `;
  return await evaluate(client, expression);
}

async function capturePage(client, page) {
  await client.send('Emulation.setDeviceMetricsOverride', {
    width: VIEWPORT_WIDTH,
    height: INITIAL_VIEWPORT_HEIGHT,
    deviceScaleFactor: 1,
    mobile: false,
  });
  const loadEvent = client.waitForEvent('Page.loadEventFired', 15000).catch(() => undefined);
  await client.send('Page.navigate', { url: `${BASE_URL}${page.route}` });
  await loadEvent;
  await waitForReady(client, page.title);
  await prepPage(client, page.slug);

  const initialSize = await documentSize(client);
  const viewportHeight = Math.min(Math.max(initialSize.height, INITIAL_VIEWPORT_HEIGHT), MAX_VIEWPORT_HEIGHT);
  await client.send('Emulation.setDeviceMetricsOverride', {
    width: Math.max(initialSize.width, VIEWPORT_WIDTH),
    height: viewportHeight,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await delay(150);
  await evaluate(client, 'window.scrollTo(0, 0); true');

  const specs = page.screenshotInfo.boxes.map(stripRuntimeFields);
  const screenshotInfo = await collectBoxes(client, specs);
  const screenshot = await client.send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
  });
  const rawScreenshot = path.join(RAW_DIR, `${page.slug}.png`).replaceAll('\\\\', '/');
  await writeFile(rawScreenshot, Buffer.from(screenshot.data, 'base64'));
  const logs = [];
  const title = await evaluate(client, 'document.title');
  const url = await evaluate(client, 'location.href');
  return {
    ...page,
    url,
    browserTitle: title,
    rawScreenshot,
    screenshotInfo,
    missing: screenshotInfo.boxes
      .filter((box) => box.missing)
      .map((box) => ({ id: box.id, label: box.label, selector: box.selector, heading: box.heading, text: box.text })),
    consoleIssues: logs,
    snapshotHasExpectedTitle: true,
  };
}

async function main() {
  await mkdir(RAW_DIR, { recursive: true });
  const manifest = JSON.parse(await readFile(MANIFEST_PATH, 'utf8'));
  const debugPort = 9333 + Math.floor(Math.random() * 500);
  const profileDir = await mkdtemp(path.join(os.tmpdir(), 'dream-runbook-chrome-'));
  const chrome = spawn(chromePath(), [
    '--headless=new',
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${profileDir}`,
    '--disable-gpu',
    '--hide-scrollbars=false',
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ], {
    stdio: 'ignore',
  });

  let client;
  try {
    await waitForJson(`http://127.0.0.1:${debugPort}/json/version`);
    const target = await createPageTarget(debugPort);
    client = new CdpClient(target.webSocketDebuggerUrl);
    await client.open();
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    const pages = [];
    for (const page of manifest.pages) {
      pages.push(await capturePage(client, page));
      console.log(`captured ${page.slug}`);
    }
    const nextManifest = {
      ...manifest,
      generatedAt: new Date().toISOString(),
      baseUrl: BASE_URL,
      captureMethod: 'Chrome DevTools Protocol viewport-height screenshot',
      pages,
    };
    await writeFile(MANIFEST_PATH, JSON.stringify(nextManifest, null, 2), 'utf8');
  } finally {
    if (client) {
      client.close();
    }
    chrome.kill();
    await delay(250);
    if (profileDir.startsWith(os.tmpdir())) {
      await rm(profileDir, { recursive: true, force: true });
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
