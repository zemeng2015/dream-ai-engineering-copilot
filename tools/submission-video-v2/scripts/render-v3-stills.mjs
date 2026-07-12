// SPDX-License-Identifier: Apache-2.0

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';

const here = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(here, '..');
const outputDir = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(projectDir, 'out', 'v3-stills');
const frames = [
  240, 620, 900,
  1150, 1330,
  1500, 1720,
  1900, 2070,
  2300, 2700,
  3150, 3450,
  3750, 4250, 4450,
];

fs.mkdirSync(outputDir, { recursive: true });
for (const file of fs.readdirSync(outputDir)) {
  if (/^shot-\d+\.png$/.test(file)) fs.rmSync(path.join(outputDir, file));
}

const serveUrl = await bundle({
  entryPoint: path.join(projectDir, 'src', 'index.ts'),
});
const composition = await selectComposition({
  serveUrl,
  id: 'DreamV3Full',
  logLevel: 'warn',
});

for (const [index, frame] of frames.entries()) {
  const output = path.join(outputDir, `shot-${String(index + 1).padStart(2, '0')}.png`);
  await renderStill({
    serveUrl,
    composition,
    frame,
    output,
    imageFormat: 'png',
    logLevel: 'warn',
  });
}

const contactSheet = path.join(outputDir, 'dream-v3-stills-contact-sheet.png');
execFileSync(
  'ffmpeg',
  [
    '-hide_banner', '-loglevel', 'error', '-y',
    '-framerate', '1', '-start_number', '1', '-i', path.join(outputDir, 'shot-%02d.png'),
    '-vf', `scale=460:-1,tile=4x4:nb_frames=${frames.length}:padding=8:margin=8:color=white`,
    '-frames:v', '1',
    contactSheet,
  ],
  { stdio: 'inherit' },
);

console.log(JSON.stringify({
  ok: true,
  frames,
  outputDir,
  contactSheet,
}, null, 2));
