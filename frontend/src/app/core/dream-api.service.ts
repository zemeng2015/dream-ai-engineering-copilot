import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import {
  KnowledgeChunk,
  PrReviewInput,
  PrReviewResult,
  RequirementDraftInput,
  RequirementDraftResult,
} from './dream-models';
import { MockDreamService } from './mock-dream.service';

interface ApiGenerationResponse {
  run_id: string;
  markdown: string;
  sources_used: string[];
  warnings: string[];
}

@Injectable({ providedIn: 'root' })
export class DreamApiService {
  private readonly http = inject(HttpClient);
  private readonly mock = inject(MockDreamService);
  private readonly baseUrl = 'http://127.0.0.1:8000';

  draftRequirementWithOpenAI(input: RequirementDraftInput): Observable<RequirementDraftResult> {
    const fallback = this.mock.draftRequirement(input);
    return this.http
      .post<ApiGenerationResponse>(`${this.baseUrl}/requirements/draft`, {
        team_id: input.teamId,
        rough_business_request: input.roughBusinessRequest,
        app: input.app,
        component: input.component,
        top_k: input.topK,
        llm_provider: 'openai-compatible',
      })
      .pipe(
        map((response) => ({
          ...fallback,
          run: {
            ...fallback.run,
            runId: response.run_id,
            modelProvider: 'openai-compatible',
            modelName: 'server-configured',
            outputPath: `artifacts/requirement-draft-${response.run_id}.md`,
            sourcesUsed: response.sources_used,
          },
          markdown: response.markdown,
          sourcesUsed: sourceChunksFromPaths(response.sources_used, fallback.sourcesUsed),
          warnings: response.warnings,
        })),
      );
  }

  reviewPrWithOpenAI(input: PrReviewInput): Observable<PrReviewResult> {
    const fallback = this.mock.reviewPr(input);
    return this.http
      .post<ApiGenerationResponse>(`${this.baseUrl}/review/pr`, {
        team_id: input.teamId,
        pr_diff_path: 'examples/pr-diffs/DFP-110-output-collector-idempotency.diff',
        jira_context_path:
          'knowledge_packs/demo_team/docs/historical-jira/DFP-110-output-collection-idempotency.md',
        repo_name: 'dfp-demo-repo',
        app: input.app,
        component: input.component,
        top_k: input.topK,
        llm_provider: 'openai-compatible',
      })
      .pipe(
        map((response) => ({
          ...fallback,
          run: {
            ...fallback.run,
            runId: response.run_id,
            modelProvider: 'openai-compatible',
            modelName: 'server-configured',
            outputPath: `artifacts/pr-review-summary-${response.run_id}.md`,
            sourcesUsed: response.sources_used,
          },
          markdown: response.markdown,
          sourcesUsed: sourceChunksFromPaths(response.sources_used, fallback.sourcesUsed),
          warnings: response.warnings,
        })),
      );
  }
}

function sourceChunksFromPaths(paths: string[], fallbackSources: KnowledgeChunk[]): KnowledgeChunk[] {
  const known = new Map(fallbackSources.map((source) => [source.sourcePath, source]));
  return paths.map(
    (sourcePath, index) =>
      known.get(sourcePath) ?? {
        id: `api-source-${index}`,
        title: titleFromPath(sourcePath),
        sourcePath,
        excerpt: 'Source returned by the FastAPI generation endpoint.',
        concepts: [],
        sourceType: sourcePath.includes('/test/') || sourcePath.toLowerCase().includes('test')
          ? 'test_file'
          : sourcePath.endsWith('.java') || sourcePath.endsWith('.ts') || sourcePath.endsWith('.py')
            ? 'code_file'
            : sourcePath.includes('/incidents/')
              ? 'incident'
              : sourcePath.includes('/historical-jira/')
                ? 'historical_jira'
                : sourcePath.includes('/historical-pr/')
                  ? 'historical_pr'
                  : sourcePath.includes('/concepts/')
                    ? 'concept_memory'
                    : 'domain_doc',
        metadata: {
          teamId: 'demo_team',
          app: 'ForecastDemo',
          component: 'api-source',
          docType: 'api',
        },
      },
  );
}

function titleFromPath(sourcePath: string): string {
  const leaf = sourcePath.split('/').pop() || sourcePath;
  return leaf.replace(/[-_]/g, ' ').replace(/\.\w+$/, '');
}
