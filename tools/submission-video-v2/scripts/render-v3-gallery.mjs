// SPDX-License-Identifier: Apache-2.0

import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';

const here = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(here, '..');
const repoDir = path.resolve(projectDir, '..', '..');
const outputDir = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(repoDir, 'artifacts', 'qwencloud-proof', 'video-v3', 'devpost-gallery-v3');
const canonicalThumbnailPath = path.join(repoDir, 'docs', 'assets', 'qwencloud-video-thumbnail.png');
const thumbnailPath = path.join(repoDir, 'artifacts', 'qwencloud-proof', 'video-v3', 'dream-v3-thumbnail.png');
const gallery = [
  ['DreamGalleryV3Hero', '01-dream-one-current-truth.png'],
  ['DreamGalleryV3Live', '02-live-qwen-three-sessions.png'],
  ['DreamGalleryV3Durability', '03-fc-tablestore-durability.png'],
  ['DreamGalleryV3Evidence', '04-alibaba-architecture-measurement.png'],
];

fs.mkdirSync(outputDir, { recursive: true });
fs.mkdirSync(path.dirname(canonicalThumbnailPath), { recursive: true });
fs.mkdirSync(path.dirname(thumbnailPath), { recursive: true });
const serveUrl = await bundle({ entryPoint: path.join(projectDir, 'src', 'index.ts') });

const records = [];
for (const [index, [id, file]] of gallery.entries()) {
  const composition = await selectComposition({ serveUrl, id, logLevel: 'warn' });
  const output = path.join(outputDir, file);
  await renderStill({ serveUrl, composition, output, imageFormat: 'png', logLevel: 'warn' });
  const bytes = fs.readFileSync(output);
  if (bytes.length >= 5_000_000) throw new Error(`Devpost gallery asset exceeds 5 MB: ${file}`);
  records.push({
    id,
    file,
    bytes: bytes.length,
    sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
  });
  fs.copyFileSync(output, path.join(outputDir, `contact-${String(index + 1).padStart(2, '0')}.png`));
}

const thumbnail = await selectComposition({ serveUrl, id: 'DreamV3Thumbnail', logLevel: 'warn' });
await renderStill({ serveUrl, composition: thumbnail, output: canonicalThumbnailPath, imageFormat: 'png', logLevel: 'warn' });
fs.copyFileSync(canonicalThumbnailPath, thumbnailPath);
const thumbnailBytes = fs.readFileSync(canonicalThumbnailPath);

const contactSheet = path.join(outputDir, 'gallery-v3-contact-sheet.png');
execFileSync(
  'ffmpeg',
  [
    '-hide_banner', '-loglevel', 'error', '-y',
    '-framerate', '1', '-start_number', '1', '-i', path.join(outputDir, 'contact-%02d.png'),
    '-vf', 'scale=450:-1,tile=2x2:nb_frames=4:padding=8:margin=8:color=white',
    '-frames:v', '1', contactSheet,
  ],
  { stdio: 'inherit' },
);
for (let index = 1; index <= gallery.length; index += 1) {
  fs.rmSync(path.join(outputDir, `contact-${String(index).padStart(2, '0')}.png`), { force: true });
}

const manifest = {
  generatedAt: new Date().toISOString(),
  format: { width: 1800, height: 1200, maximumBytes: 5_000_000 },
  assets: records,
  thumbnail: {
    file: path.relative(repoDir, canonicalThumbnailPath).replaceAll('\\', '/'),
    artifactCopy: path.relative(repoDir, thumbnailPath).replaceAll('\\', '/'),
    bytes: thumbnailBytes.length,
    sha256: crypto.createHash('sha256').update(thumbnailBytes).digest('hex'),
  },
};
fs.writeFileSync(path.join(outputDir, 'gallery-v3-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(JSON.stringify({
  ok: true,
  outputDir,
  contactSheet,
  canonicalThumbnailPath,
  thumbnailPath,
  manifest,
}, null, 2));
