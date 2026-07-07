// SPDX-License-Identifier: Apache-2.0

import type { IntakeDocument } from './dream-api.service';

export function sourceDocumentRoute(
  sourcePath: string,
  intakeDocuments: IntakeDocument[],
): string[] | null {
  const document = intakeDocuments.find((item) => sourceMatchesDocument(sourcePath, item));
  return document ? ['/memory', document.documentId] : null;
}

export function sourceMatchesDocument(sourcePath: string, document: IntakeDocument): boolean {
  const normalizedSource = normalizeSourcePath(sourcePath);
  return [document.promotedPath, document.storedPath, document.originalPath].some((candidate) => {
    const normalizedCandidate = normalizeSourcePath(candidate || '');
    return (
      normalizedCandidate.length > 0 &&
      (normalizedSource === normalizedCandidate ||
        normalizedSource.endsWith(`/${normalizedCandidate}`) ||
        normalizedCandidate.endsWith(`/${normalizedSource}`))
    );
  });
}

export function normalizeSourcePath(value: string): string {
  const normalized = value
    .split('#')[0]
    .replace(/\\/g, '/')
    .trim()
    .toLowerCase();
  const marker = '/dream-ai-engineering-copilot/';
  const markerIndex = normalized.indexOf(marker);
  if (markerIndex >= 0) {
    return normalized.slice(markerIndex + marker.length);
  }
  return normalized.replace(/^\.\//, '');
}
