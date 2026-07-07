// SPDX-License-Identifier: Apache-2.0

import type { IntakeDocument } from './dream-api.service';
import { normalizeSourcePath, sourceDocumentRoute } from './source-provenance';

describe('source provenance helpers', () => {
  const document: IntakeDocument = {
    documentId: 'intake-123',
    teamId: 'demo_team',
    title: 'Output Reconciliation',
    documentType: 'runbooks',
    originalPath: 'uploaded://output-reconciliation.md',
    storedPath: 'artifacts/intake/uploads/intake-123.md',
    promotedPath:
      'knowledge_packs/demo_team/docs/runbooks/output-reconciliation-intake-123.md',
    status: 'promoted',
    createdAt: '2026-07-06T00:00:00Z',
    updatedAt: '2026-07-06T00:00:00Z',
    warnings: [],
  };

  it('normalizes workspace paths and drops fragments', () => {
    expect(
      normalizeSourcePath(
        'C:\\Users\\wangz\\OneDrive\\Documents\\Test Generation\\dream-ai-engineering-copilot\\knowledge_packs\\demo_team\\docs\\runbooks\\output-reconciliation-intake-123.md#section',
      ),
    ).toBe('knowledge_packs/demo_team/docs/runbooks/output-reconciliation-intake-123.md');
  });

  it('returns a memory detail route for matched promoted sources', () => {
    expect(
      sourceDocumentRoute(
        'knowledge_packs/demo_team/docs/runbooks/output-reconciliation-intake-123.md',
        [document],
      ),
    ).toEqual(['/memory', 'intake-123']);
  });

  it('does not link unrelated sources', () => {
    expect(sourceDocumentRoute('knowledge_packs/demo_team/docs/runbooks/other.md', [document])).toBeNull();
  });
});
