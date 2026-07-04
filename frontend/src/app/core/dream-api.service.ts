// SPDX-License-Identifier: Apache-2.0

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map, switchMap } from 'rxjs';

import {
  AuditRun,
  ClarificationQuestion,
  CodebaseFile,
  ContextEvidence,
  EvaluationDimension,
  EvaluationScorecard,
  EvidenceSourceType,
  ImpactItem,
  KnowledgeChunk,
  PrReviewInput,
  PrReviewResult,
  RequirementCase,
  RequirementDraftInput,
  RequirementDraftResult,
  RunStatus,
  WorkflowType,
} from './dream-models';

interface ApiGenerationResponse {
  run_id: string;
  markdown: string;
  sources_used: string[];
  warnings: string[];
}

interface ApiRequirementCaseSnapshot {
  case: ApiRequirementCase;
  evidence: ApiContextEvidence[];
  impact_items: ApiImpactItem[];
  questions: ApiClarificationQuestion[];
  engineering_brief?: ApiMarkdownArtifact | null;
  jira_draft?: ApiJiraDraft | null;
  jira_readiness?: ApiJiraReadiness | null;
  warnings: string[];
}

interface ApiRequirementCase {
  case_id: string;
  team_id: string;
  title: string;
  raw_request: string;
  created_by_role: string | null;
  target_app: string | null;
  target_component: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ApiContextEvidence {
  evidence_id: string;
  case_id: string;
  source_type: string;
  source_path: string;
  title: string;
  excerpt: string;
  relevance_score: number;
  reason: string;
}

interface ApiImpactItem {
  impact_id: string;
  case_id: string;
  area_type: string;
  name: string;
  description: string;
  confidence: number;
  sources: string[];
  reason: string;
}

interface ApiClarificationQuestion {
  question_id: string;
  case_id: string;
  target_role: string;
  question: string;
  why_it_matters: string;
  related_sources: string[];
  status: string;
  answer?: string | null;
  answered_by?: string | null;
  answered_at?: string | null;
}

interface ApiMarkdownArtifact {
  markdown: string;
  sources_used: string[];
  warnings: string[];
}

interface ApiJiraDraft extends ApiMarkdownArtifact {
  case_id: string;
}

interface ApiJiraReadiness {
  case_id: string;
  ready: boolean;
  status: string;
  answered_questions: number;
  open_questions: number;
  evidence_items: number;
  impact_items: number;
  jira_draft_exists: boolean;
  blocking_reasons: string[];
  recommendations: string[];
}

interface ApiEvaluationResult {
  scorecard: ApiEvaluationScorecard;
  markdown_report: string;
  json_path: string;
  markdown_path: string;
  warnings: string[];
}

interface ApiEvaluationScorecard {
  evaluation_id: string;
  target_type: string;
  target_id?: string | null;
  run_id?: string | null;
  case_id?: string | null;
  team_id?: string | null;
  repo_name?: string | null;
  created_at: string;
  overall_score: number;
  grade: string;
  pass_status: string;
  dimensions: ApiEvaluationDimension[];
  missing_critical_items: string[];
  hallucination_warnings: string[];
  source_coverage: Record<string, boolean>;
  recommendations: string[];
  evaluated_artifact_path?: string | null;
  output_path?: string | null;
}

interface ApiEvaluationDimension {
  name: string;
  score: number;
  weight: number;
  passed: boolean;
  rationale: string;
  evidence: string[];
  missing_items: string[];
  recommendations: string[];
}

interface ApiAuditRecord {
  run_id: string;
  timestamp: string;
  use_case: string;
  team_id: string;
  case_id?: string | null;
  repo_name?: string | null;
  retrieved_source_paths: string[];
  model_provider: string;
  model_name: string;
  output_path: string;
  status: string;
  warnings: string[];
}

interface ApiIntakeDocument {
  document_id: string;
  team_id: string;
  title: string;
  document_type: string;
  original_path: string;
  stored_path: string;
  promoted_path?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  warnings: string[];
}

interface ApiCodebaseFile {
  file_id: string;
  path: string;
  language: string;
  size_bytes: number;
  line_count: number;
  role: string;
  summary: string;
  symbols: string[];
  concepts: string[];
}

interface ApiCodebaseConcept {
  concept: string;
  related_files: string[];
  related_symbols: string[];
  related_tests: string[];
  related_docs?: string[];
  confidence: number;
  reason: string;
}

interface ApiCodebaseSearchResult {
  result_type: string;
  title: string;
  source_path: string;
  excerpt: string;
  score: number;
  reason: string;
  metadata: Record<string, string>;
}

interface ApiRepoIndex {
  repo_id?: string;
  team_id: string;
  repo_name: string;
  repo_path: string;
  indexed_at: string;
  files: ApiCodebaseFile[];
  symbols: unknown[];
  tests: unknown[];
  dependencies: unknown[];
  concepts: ApiCodebaseConcept[];
  summary: string;
  warnings: string[];
}

interface ApiCodebaseIndexArtifact {
  index_path: string;
  index: ApiRepoIndex;
}

interface ApiCodebaseFileContent {
  path: string;
  language: string;
  role: string;
  size_bytes: number;
  line_count: number;
  content: string;
}

export interface IntakeDocument {
  documentId: string;
  teamId: string;
  title: string;
  documentType: string;
  originalPath: string;
  storedPath: string;
  promotedPath?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
  warnings: string[];
}

export interface CodebaseIndexFile {
  fileId: string;
  path: string;
  language: string;
  sizeBytes: number;
  lineCount: number;
  role: string;
  summary: string;
  symbols: string[];
  concepts: string[];
}

export interface CodebaseConcept {
  concept: string;
  relatedFiles: string[];
  relatedSymbols: string[];
  relatedTests: string[];
  relatedDocs: string[];
  confidence: number;
  reason: string;
}

export interface CodebaseSearchItem {
  resultType: string;
  title: string;
  sourcePath: string;
  excerpt: string;
  score: number;
  reason: string;
  metadata: Record<string, string>;
}

export interface CodebaseIndexSummary {
  teamId: string;
  repoName: string;
  repoPath: string;
  indexedAt: string;
  fileCount: number;
  symbolCount: number;
  testCount: number;
  conceptCount: number;
  summary: string;
  warnings: string[];
}

export interface CodebaseIndexArtifact {
  indexPath: string;
  index: Record<string, unknown>;
  summary: CodebaseIndexSummary;
  rawJson: string;
}

export interface CodebaseFileContent {
  path: string;
  language: string;
  role: string;
  sizeBytes: number;
  lineCount: number;
  content: string;
}

@Injectable({ providedIn: 'root' })
export class DreamApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://127.0.0.1:8000';

  draftRequirementWithOpenAI(input: RequirementDraftInput): Observable<RequirementDraftResult> {
    return this.http
      .post<ApiRequirementCaseSnapshot>(`${this.baseUrl}/requirement-cases`, {
        team_id: input.teamId,
        raw_request: input.roughBusinessRequest,
        created_by_role: input.role || 'BA',
        target_app: input.app,
        target_component: input.component,
      })
      .pipe(
        switchMap((snapshot) =>
          this.http.post<ApiRequirementCaseSnapshot>(
            `${this.baseUrl}/requirement-cases/${snapshot.case.case_id}/analyze`,
            {},
          ),
        ),
        switchMap((snapshot) =>
          this.generateAndEvaluateRequirementCase(input, snapshot.case.case_id),
        ),
      );
  }

  regenerateRequirementCaseWithOpenAI(
    input: RequirementDraftInput,
    caseId: string,
  ): Observable<RequirementDraftResult> {
    return this.generateAndEvaluateRequirementCase(input, caseId);
  }

  answerRequirementQuestion(
    caseId: string,
    questionId: string,
    answer: string,
  ): Observable<ClarificationQuestion> {
    return this.http
      .post<ApiClarificationQuestion>(
        `${this.baseUrl}/requirement-cases/${caseId}/questions/${questionId}/answer`,
        {
          answer,
          answered_by: 'Demo Reviewer',
        },
      )
      .pipe(map((question) => mapQuestion(question)));
  }

  getEvaluationRun(evaluationId: string): Observable<EvaluationScorecard> {
    return this.http
      .get<ApiEvaluationScorecard>(`${this.baseUrl}/eval/runs/${evaluationId}`)
      .pipe(map((scorecard) => mapScorecard(scorecard)));
  }

  getRequirementCase(caseId: string): Observable<RequirementCase> {
    return this.http
      .get<ApiRequirementCaseSnapshot>(`${this.baseUrl}/requirement-cases/${caseId}`)
      .pipe(map((snapshot) => mapRequirementCase(snapshot)));
  }

  listAuditRuns(defaultApp = 'Demo'): Observable<AuditRun[]> {
    return this.http
      .get<ApiAuditRecord[]>(`${this.baseUrl}/audit/runs`)
      .pipe(map((records) => records.map((record) => mapAuditRun(record, defaultApp))));
  }

  listEvaluationRuns(): Observable<EvaluationScorecard[]> {
    return this.http
      .get<ApiEvaluationScorecard[]>(`${this.baseUrl}/eval/runs`)
      .pipe(map((scorecards) => scorecards.map(mapScorecard)));
  }

  listRequirementCases(): Observable<RequirementCase[]> {
    return this.http
      .get<ApiRequirementCaseSnapshot[]>(`${this.baseUrl}/requirement-cases`)
      .pipe(map((snapshots) => snapshots.map(mapRequirementCase)));
  }

  listIntakeDocuments(): Observable<IntakeDocument[]> {
    return this.http
      .get<ApiIntakeDocument[]>(`${this.baseUrl}/intake/documents`)
      .pipe(map((documents) => documents.map(mapIntakeDocument)));
  }

  uploadIntakeDocument(input: {
    teamId: string;
    filePath: string;
    documentType: string;
    title?: string;
  }): Observable<IntakeDocument> {
    return this.http
      .post<ApiIntakeDocument>(`${this.baseUrl}/intake/documents`, {
        team_id: input.teamId,
        file_path: input.filePath,
        document_type: input.documentType,
        title: input.title || null,
      })
      .pipe(map(mapIntakeDocument));
  }

  parseIntakeDocument(documentId: string): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/intake/documents/${documentId}/parse`, {});
  }

  approveIntakeDocument(documentId: string): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/intake/drafts/draft-${documentId}/review`, {
      status: 'approved',
      reviewer: 'Demo Reviewer',
      notes: 'Approved from Memory Hub.',
    });
  }

  promoteIntakeDocument(documentId: string): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/intake/drafts/draft-${documentId}/promote`, {});
  }

  listCodebaseFiles(teamId: string, repoName: string): Observable<CodebaseIndexFile[]> {
    return this.http
      .get<ApiCodebaseFile[]>(`${this.baseUrl}/codebase/files`, {
        params: { team_id: teamId, repo_name: repoName },
      })
      .pipe(map((files) => files.map(mapCodebaseFile)));
  }

  listCodebaseConcepts(teamId: string, repoName: string): Observable<CodebaseConcept[]> {
    return this.http
      .get<ApiCodebaseConcept[]>(`${this.baseUrl}/codebase/concepts`, {
        params: { team_id: teamId, repo_name: repoName },
      })
      .pipe(map((concepts) => concepts.map(mapCodebaseConcept)));
  }

  getCodebaseIndex(teamId: string, repoName: string): Observable<CodebaseIndexArtifact> {
    return this.http
      .get<ApiCodebaseIndexArtifact>(`${this.baseUrl}/codebase/index`, {
        params: { team_id: teamId, repo_name: repoName },
      })
      .pipe(map(mapCodebaseIndexArtifact));
  }

  getCodebaseFileContent(
    teamId: string,
    repoName: string,
    filePath: string,
  ): Observable<CodebaseFileContent> {
    return this.http
      .get<ApiCodebaseFileContent>(`${this.baseUrl}/codebase/file-content`, {
        params: { team_id: teamId, repo_name: repoName, file_path: filePath },
      })
      .pipe(map(mapCodebaseFileContent));
  }

  searchCodebaseIndex(
    teamId: string,
    repoName: string,
    query: string,
    topK: number,
  ): Observable<CodebaseSearchItem[]> {
    return this.http
      .get<ApiCodebaseSearchResult[]>(`${this.baseUrl}/codebase/search`, {
        params: {
          team_id: teamId,
          repo_name: repoName,
          query,
          top_k: String(topK),
        },
      })
      .pipe(map((items) => items.map(mapCodebaseSearchItem)));
  }

  indexCodebase(
    teamId: string,
    repoPath: string,
    repoName: string,
  ): Observable<CodebaseIndexSummary> {
    return this.http
      .post<ApiRepoIndex>(`${this.baseUrl}/codebase/index`, {
        team_id: teamId,
        repo_path: repoPath,
        repo_name: repoName,
      })
      .pipe(map(mapCodebaseIndexSummary));
  }

  reviewPrWithOpenAI(input: PrReviewInput): Observable<PrReviewResult> {
    const changedFiles = extractChangedFiles(input.diffText);
    return this.http
      .post<ApiGenerationResponse>(`${this.baseUrl}/review/pr`, {
        team_id: input.teamId,
        pr_diff_text: input.diffText,
        jira_context_text: input.jiraContext,
        repo_name: 'dfp-demo-repo',
        app: input.app,
        component: input.component,
        top_k: input.topK,
        llm_provider: 'openai-compatible',
      })
      .pipe(
        switchMap((response) =>
          this.http
            .post<ApiEvaluationResult>(`${this.baseUrl}/eval/run`, {
              target_type: 'pr_review',
              run_id: response.run_id,
              team_id: input.teamId,
              repo_name: 'dfp-demo-repo',
              strict: true,
            })
            .pipe(map((evaluation) => ({ response, evaluation }))),
        ),
        switchMap(({ response, evaluation }) =>
          this.listAuditRuns(input.app).pipe(
            map((runs) =>
              this.toPrReviewResult(
                input,
                response,
                mapScorecard(evaluation.scorecard),
                runs.find((run) => run.runId === response.run_id),
                changedFiles,
              ),
            ),
          ),
        ),
      );
  }

  private toPrReviewResult(
    input: PrReviewInput,
    response: ApiGenerationResponse,
    scorecard: EvaluationScorecard,
    auditRun: AuditRun | undefined,
    changedFiles: string[],
  ): PrReviewResult {
    const codePaths = Array.from(
      new Set([
        ...changedFiles,
        ...response.sources_used.filter((sourcePath) =>
          ['code_file', 'test_file'].includes(sourceTypeFromValue('', sourcePath)),
        ),
      ]),
    );
    const run =
      auditRun ??
      buildSyntheticRun({
        runId: response.run_id,
        caseId: scorecard.caseId || response.run_id,
        teamId: input.teamId,
        app: input.app,
        status: scorecard.passStatus === 'fail' ? 'failed' : 'success',
        outputPath: `artifacts/pr-review-summary-${response.run_id}.md`,
        sourcesUsed: response.sources_used,
      });
    return {
      run,
      markdown: response.markdown,
      risk: riskFromDiff(input.diffText, changedFiles),
      sourcesUsed: sourceChunksFromPaths(
        response.sources_used,
        [],
        input.teamId,
        input.app,
        input.component,
      ),
      warnings: response.warnings,
      changedFiles,
      relatedCode: codePaths.map(codebaseFileFromPath),
      scorecard,
    };
  }

  private generateAndEvaluateRequirementCase(
    input: RequirementDraftInput,
    caseId: string,
  ): Observable<RequirementDraftResult> {
    return this.http
      .get<ApiJiraDraft>(
        `${this.baseUrl}/requirement-cases/${caseId}/jira-draft?llm_provider=openai-compatible`,
      )
      .pipe(
        switchMap(() =>
          this.http.get<ApiJiraReadiness>(
            `${this.baseUrl}/requirement-cases/${caseId}/jira-readiness`,
          ),
        ),
        switchMap(() =>
          this.http.post<ApiEvaluationResult>(`${this.baseUrl}/eval/run`, {
            target_type: 'jira_draft',
            case_id: caseId,
            team_id: input.teamId,
            strict: true,
          }),
        ),
        switchMap((evaluation) =>
          this.http
            .get<ApiRequirementCaseSnapshot>(`${this.baseUrl}/requirement-cases/${caseId}`)
            .pipe(map((snapshot) => ({ evaluation, snapshot }))),
        ),
        switchMap(({ evaluation, snapshot }) =>
          this.listAuditRuns(input.app).pipe(
            map((runs) =>
              this.toRequirementDraftResult(
                input,
                snapshot,
                mapScorecard(evaluation.scorecard),
                runs.find(
                  (run) => run.caseId === caseId && run.useCase === 'jira_draft',
                ),
              ),
            ),
          ),
        ),
      );
  }

  private toRequirementDraftResult(
    input: RequirementDraftInput,
    snapshot: ApiRequirementCaseSnapshot,
    scorecard: EvaluationScorecard,
    auditRun: AuditRun | undefined,
  ): RequirementDraftResult {
    const requirementCase = mapRequirementCase(snapshot);
    const sourcePaths =
      snapshot.jira_draft?.sources_used.length
        ? snapshot.jira_draft.sources_used
        : snapshot.evidence.map((item) => item.source_path);
    const run =
      auditRun ??
      buildSyntheticRun({
        runId: scorecard.runId || scorecard.evaluationId,
        caseId: snapshot.case.case_id,
        teamId: input.teamId,
        app: input.app,
        status: requirementCase.status === 'jira_ready_draft' ? 'jira_ready_draft' : 'warning',
        outputPath:
          scorecard.outputPath ||
          `artifacts/requirement-cases/${snapshot.case.case_id}/jira-draft.md`,
        sourcesUsed: sourcePaths,
      });
    return {
      run,
      markdown: requirementCase.jiraDraft,
      sourcesUsed: sourceChunksFromPaths(sourcePaths, [], input.teamId, input.app, input.component),
      warnings: [
        ...(snapshot.warnings ?? []),
        ...(snapshot.jira_draft?.warnings ?? []),
        ...(snapshot.jira_readiness?.blocking_reasons ?? []),
      ],
      requirementCase,
      scorecard,
    };
  }
}

function mapRequirementCase(snapshot: ApiRequirementCaseSnapshot): RequirementCase {
  const readiness = snapshot.jira_readiness;
  return {
    caseId: snapshot.case.case_id,
    title: snapshot.case.title,
    rawRequest: snapshot.case.raw_request,
    createdByRole: snapshot.case.created_by_role || 'BA',
    status: normalizeRequirementStatus(readiness?.status || snapshot.case.status),
    jiraReadinessStatus: readinessStatusFromValue(readiness?.status),
    jiraReady: readiness?.ready ?? snapshot.case.status === 'jira_ready_draft',
    confidence: confidenceForSnapshot(snapshot),
    createdAt: snapshot.case.created_at,
    updatedAt: snapshot.case.updated_at,
    evidence: snapshot.evidence.map(mapEvidence),
    impactMap: snapshot.impact_items.map(mapImpactItem),
    questions: snapshot.questions.map(mapQuestion),
    engineeringBrief: snapshot.engineering_brief?.markdown ?? '',
    jiraDraft: snapshot.jira_draft?.markdown ?? '',
  };
}

function mapEvidence(evidence: ApiContextEvidence): ContextEvidence {
  return {
    evidenceId: evidence.evidence_id,
    title: evidence.title,
    sourcePath: evidence.source_path,
    sourceType: sourceTypeFromValue(evidence.source_type, evidence.source_path),
    excerpt: evidence.excerpt,
    relevanceScore: evidence.relevance_score,
    reason: evidence.reason,
  };
}

function mapImpactItem(item: ApiImpactItem): ImpactItem {
  return {
    areaType: areaTypeFromValue(item.area_type),
    name: item.name,
    description: item.description,
    confidence: item.confidence,
    sources: item.sources,
    reason: item.reason,
  };
}

function mapQuestion(question: ApiClarificationQuestion): ClarificationQuestion {
  return {
    questionId: question.question_id,
    targetRole: targetRoleFromValue(question.target_role),
    question: question.question,
    whyItMatters: question.why_it_matters,
    relatedSources: question.related_sources,
    status: question.status === 'answered' ? 'answered' : question.status === 'waived' ? 'waived' : 'open',
    answer: question.answer ?? undefined,
    answeredBy: question.answered_by ?? undefined,
    answeredAt: question.answered_at ?? undefined,
  };
}

function mapScorecard(scorecard: ApiEvaluationScorecard): EvaluationScorecard {
  const targetId = scorecard.target_id || scorecard.case_id || scorecard.evaluation_id;
  return {
    evaluationId: scorecard.evaluation_id,
    targetType: targetTypeFromValue(scorecard.target_type),
    targetId,
    caseId: scorecard.case_id ?? undefined,
    runId: scorecard.run_id ?? undefined,
    teamId: scorecard.team_id ?? undefined,
    outputPath: scorecard.output_path ?? undefined,
    overallScore: Number(scorecard.overall_score.toFixed(2)),
    grade: gradeFromValue(scorecard.grade),
    passStatus: passStatusFromValue(scorecard.pass_status),
    sourceCoverage: scorecard.source_coverage,
    dimensions: scorecard.dimensions.map(mapDimension),
    missingCriticalItems: scorecard.missing_critical_items,
    hallucinationWarnings: scorecard.hallucination_warnings,
    recommendations: scorecard.recommendations,
  };
}

function mapDimension(dimension: ApiEvaluationDimension): EvaluationDimension {
  return {
    name: dimension.name,
    score: Number(dimension.score.toFixed(2)),
    weight: dimension.weight,
    passed: dimension.passed,
    rationale: dimension.rationale,
    evidence: dimension.evidence,
    missingItems: dimension.missing_items,
    recommendations: dimension.recommendations,
  };
}

function mapAuditRun(record: ApiAuditRecord, defaultApp: string): AuditRun {
  return {
    runId: record.run_id,
    caseId: record.case_id ?? null,
    useCase: workflowTypeFromValue(record.use_case),
    teamId: record.team_id,
    app: record.repo_name || record.case_id || defaultApp,
    status: runStatusFromValue(record.status),
    startedAt: record.timestamp,
    duration: 'recorded',
    modelProvider: record.model_provider,
    modelName: record.model_name,
    outputPath: record.output_path,
    warnings: record.warnings,
    sourcesUsed: record.retrieved_source_paths,
  };
}

function mapIntakeDocument(document: ApiIntakeDocument): IntakeDocument {
  return {
    documentId: document.document_id,
    teamId: document.team_id,
    title: document.title,
    documentType: document.document_type,
    originalPath: document.original_path,
    storedPath: document.stored_path,
    promotedPath: document.promoted_path,
    status: document.status,
    createdAt: document.created_at,
    updatedAt: document.updated_at,
    warnings: document.warnings,
  };
}

function mapCodebaseFile(file: ApiCodebaseFile): CodebaseIndexFile {
  return {
    fileId: file.file_id,
    path: file.path,
    language: file.language,
    sizeBytes: file.size_bytes,
    lineCount: file.line_count,
    role: file.role,
    summary: file.summary,
    symbols: file.symbols,
    concepts: file.concepts,
  };
}

function mapCodebaseConcept(concept: ApiCodebaseConcept): CodebaseConcept {
  return {
    concept: concept.concept,
    relatedFiles: concept.related_files,
    relatedSymbols: concept.related_symbols,
    relatedTests: concept.related_tests,
    relatedDocs: concept.related_docs ?? [],
    confidence: concept.confidence,
    reason: concept.reason,
  };
}

function mapCodebaseSearchItem(item: ApiCodebaseSearchResult): CodebaseSearchItem {
  return {
    resultType: item.result_type,
    title: item.title,
    sourcePath: item.source_path,
    excerpt: item.excerpt,
    score: item.score,
    reason: item.reason,
    metadata: item.metadata,
  };
}

function mapCodebaseIndexSummary(index: ApiRepoIndex): CodebaseIndexSummary {
  return {
    teamId: index.team_id,
    repoName: index.repo_name,
    repoPath: index.repo_path,
    indexedAt: index.indexed_at,
    fileCount: index.files.length,
    symbolCount: index.symbols.length,
    testCount: index.tests.length,
    conceptCount: index.concepts.length,
    summary: index.summary,
    warnings: index.warnings,
  };
}

function mapCodebaseIndexArtifact(artifact: ApiCodebaseIndexArtifact): CodebaseIndexArtifact {
  const index = artifact.index as unknown as Record<string, unknown>;
  return {
    indexPath: artifact.index_path,
    index,
    summary: mapCodebaseIndexSummary(artifact.index),
    rawJson: JSON.stringify(index, null, 2),
  };
}

function mapCodebaseFileContent(file: ApiCodebaseFileContent): CodebaseFileContent {
  return {
    path: file.path,
    language: file.language,
    role: file.role,
    sizeBytes: file.size_bytes,
    lineCount: file.line_count,
    content: file.content,
  };
}

function sourceChunksFromPaths(
  paths: string[],
  fallbackSources: KnowledgeChunk[] = [],
  teamId = 'demo_team',
  app = 'ForecastDemo',
  component = 'api-source',
): KnowledgeChunk[] {
  const known = new Map(fallbackSources.map((source) => [source.sourcePath, source]));
  return paths.map(
    (sourcePath, index) =>
      known.get(sourcePath) ?? {
        id: `api-source-${index}`,
        title: titleFromPath(sourcePath),
        sourcePath,
        excerpt: 'Source returned by the FastAPI requirement case workflow.',
        concepts: conceptsFromPath(sourcePath),
        sourceType: sourceTypeFromValue('', sourcePath),
        metadata: {
          teamId,
          app,
          component: componentFromPath(sourcePath, component),
          docType: docTypeFromPath(sourcePath),
        },
      },
  );
}

function extractChangedFiles(diffText: string): string[] {
  const files: string[] = [];
  for (const line of diffText.split(/\r?\n/)) {
    if (!line.startsWith('diff --git ')) {
      continue;
    }
    const parts = line.split(/\s+/);
    const candidate = parts[3]?.replace(/^b\//, '');
    if (candidate) {
      files.push(normalizeRepoPath(candidate));
    }
  }
  return Array.from(new Set(files));
}

function normalizeRepoPath(path: string): string {
  return path.replace(/^examples\/dfp-demo-repo\//, '').replace(/^\.?\//, '');
}

function riskFromDiff(diffText: string, changedFiles: string[]): PrReviewResult['risk'] {
  const changedLineCount = diffText
    .split(/\r?\n/)
    .filter((line) => /^[+-]/.test(line) && !/^(---|\+\+\+)/.test(line)).length;
  if (changedFiles.length >= 8 || changedLineCount >= 260) {
    return 'High';
  }
  if (changedFiles.length >= 4 || changedLineCount >= 80) {
    return 'Medium';
  }
  return 'Low';
}

function codebaseFileFromPath(path: string): CodebaseFile {
  const normalized = normalizeRepoPath(path);
  return {
    id: `api-code-${normalized}`,
    path: normalized,
    layer: layerFromPath(normalized),
    language: languageFromPath(normalized),
    role: /test/i.test(normalized) ? 'test' : /\.(md|mdx)$/i.test(normalized) ? 'docs' : 'source',
    summary: `Codebase evidence returned by the FastAPI PR review workflow.`,
    concepts: conceptsFromPath(normalized),
    symbols: [titleFromPath(normalized)].filter(Boolean),
    relatedTests: [],
  };
}

function layerFromPath(path: string): CodebaseFile['layer'] {
  if (path.includes('/test/') || path.toLowerCase().includes('test')) return 'test';
  if (path.startsWith('frontend/')) return 'frontend';
  if (path.startsWith('aws/')) return 'aws';
  if (path.startsWith('python-')) return 'python';
  return 'backend';
}

function languageFromPath(path: string): CodebaseFile['language'] {
  if (/\.(ts|tsx)$/i.test(path)) return 'typescript';
  if (/\.java$/i.test(path)) return 'java';
  if (/\.py$/i.test(path)) return 'python';
  if (/\.json$/i.test(path)) return 'json';
  return 'markdown';
}

function buildSyntheticRun(input: {
  runId: string;
  caseId: string;
  teamId: string;
  app: string;
  status: RunStatus;
  outputPath: string;
  sourcesUsed: string[];
}): AuditRun {
  return {
    runId: input.runId,
    caseId: input.caseId,
    useCase: 'jira_draft',
    teamId: input.teamId,
    app: input.app,
    status: input.status,
    startedAt: new Date().toISOString(),
    duration: 'recorded',
    modelProvider: 'openai-compatible',
    modelName: 'server-configured',
    outputPath: input.outputPath,
    warnings: [],
    sourcesUsed: input.sourcesUsed,
  };
}

function confidenceForSnapshot(snapshot: ApiRequirementCaseSnapshot): number {
  const evidenceScore = Math.min(0.25, snapshot.evidence.length * 0.0125);
  const impactScore = Math.min(0.15, snapshot.impact_items.length * 0.025);
  const readinessScore = snapshot.jira_readiness?.ready ? 0.1 : 0;
  return Number((0.55 + evidenceScore + impactScore + readinessScore).toFixed(2));
}

function sourceTypeFromValue(value: string, sourcePath: string): EvidenceSourceType {
  const normalized = value || sourceTypeNameFromPath(sourcePath);
  const allowed: EvidenceSourceType[] = [
    'domain_doc',
    'architecture_doc',
    'runbook',
    'incident',
    'historical_jira',
    'historical_pr',
    'testing_doc',
    'concept_memory',
    'graph_evidence',
    'code_file',
    'test_file',
  ];
  return allowed.includes(normalized as EvidenceSourceType)
    ? (normalized as EvidenceSourceType)
    : sourceTypeNameFromPath(sourcePath);
}

function sourceTypeNameFromPath(sourcePath: string): EvidenceSourceType {
  const path = sourcePath.toLowerCase();
  if (path.includes('/architecture/')) return 'architecture_doc';
  if (path.includes('/runbooks/')) return 'runbook';
  if (path.includes('/incidents/') || path.includes('inc-')) return 'incident';
  if (path.includes('/historical-jira/') || path.includes('dfp-')) return 'historical_jira';
  if (path.includes('/historical-pr/') || path.includes('pr-')) return 'historical_pr';
  if (path.includes('/testing/')) return 'testing_doc';
  if (path.includes('/concepts/')) return 'concept_memory';
  if (path.includes('evidence-graph')) return 'graph_evidence';
  if (path.includes('/test/') || path.toLowerCase().includes('test')) return 'test_file';
  if (/\.(java|ts|py|tsx|jsx)$/i.test(sourcePath)) return 'code_file';
  return 'domain_doc';
}

function areaTypeFromValue(value: string): ImpactItem['areaType'] {
  const allowed: ImpactItem['areaType'][] = [
    'frontend',
    'backend',
    'api',
    'data',
    'workflow',
    'test',
    'ops',
    'security',
  ];
  return allowed.includes(value as ImpactItem['areaType'])
    ? (value as ImpactItem['areaType'])
    : 'workflow';
}

function targetRoleFromValue(value: string): ClarificationQuestion['targetRole'] {
  const normalized = value.toUpperCase();
  const allowed: ClarificationQuestion['targetRole'][] = [
    'BA',
    'TL',
    'FE',
    'BE',
    'QA',
    'OPS',
    'SECURITY',
  ];
  return allowed.includes(normalized as ClarificationQuestion['targetRole'])
    ? (normalized as ClarificationQuestion['targetRole'])
    : 'BA';
}

function normalizeRequirementStatus(value: string): RequirementCase['status'] {
  const allowed: RequirementCase['status'][] = [
    'created',
    'analyzed',
    'brief_generated',
    'questions_answered',
    'jira_draft_needs_answers',
    'jira_ready_draft',
    'closed',
  ];
  return allowed.includes(value as RequirementCase['status'])
    ? (value as RequirementCase['status'])
    : 'analyzed';
}

function readinessStatusFromValue(
  value: string | undefined,
): RequirementCase['jiraReadinessStatus'] {
  if (value === 'jira_draft_needs_answers' || value === 'jira_ready_draft') {
    return value;
  }
  return undefined;
}

function targetTypeFromValue(value: string): EvaluationScorecard['targetType'] {
  const allowed: EvaluationScorecard['targetType'][] = [
    'requirement_case',
    'engineering_brief',
    'jira_draft',
    'pr_review',
    'testgen_report',
  ];
  return allowed.includes(value as EvaluationScorecard['targetType'])
    ? (value as EvaluationScorecard['targetType'])
    : 'requirement_case';
}

function gradeFromValue(value: string): EvaluationScorecard['grade'] {
  const normalized = value.toUpperCase();
  return ['A', 'B', 'C', 'D', 'F'].includes(normalized)
    ? (normalized as EvaluationScorecard['grade'])
    : 'F';
}

function passStatusFromValue(value: string): EvaluationScorecard['passStatus'] {
  if (value === 'pass' || value === 'warning' || value === 'fail') {
    return value;
  }
  return value === 'failed' ? 'fail' : 'warning';
}

function workflowTypeFromValue(value: string): WorkflowType {
  const allowed: WorkflowType[] = [
    'requirement_draft',
    'requirement_case',
    'requirement_case_create',
    'requirement_case_analysis',
    'requirement_question_answer',
    'engineering_brief',
    'jira_draft',
    'jira_readiness_check',
    'pr_review_summary',
    'knowledge_search',
    'knowledge_intake',
    'knowledge_intake_upload',
    'knowledge_intake_parse',
    'knowledge_intake_review',
    'knowledge_intake_promote',
    'context_intelligence',
    'codebase_index',
    'evidence_graph',
    'testgen_stub',
    'audit_eval',
    'evaluation_scorecard',
    'eval_scorecard',
  ];
  return allowed.includes(value as WorkflowType) ? (value as WorkflowType) : 'audit_eval';
}

function runStatusFromValue(value: string): RunStatus {
  const allowed: RunStatus[] = [
    'success',
    'completed',
    'created',
    'answered',
    'needs_review',
    'warning',
    'failed',
    'fail',
    'pass',
    'stub_only',
    'jira_draft_needs_answers',
    'jira_ready_draft',
  ];
  return allowed.includes(value as RunStatus) ? (value as RunStatus) : 'success';
}

function titleFromPath(sourcePath: string): string {
  const leaf = sourcePath.split('/').pop() || sourcePath;
  return leaf.replace(/[-_]/g, ' ').replace(/\.\w+$/, '');
}

function docTypeFromPath(sourcePath: string): string {
  const path = sourcePath.toLowerCase();
  if (path.includes('/runbooks/')) return 'runbooks';
  if (path.includes('/architecture/')) return 'architecture';
  if (path.includes('/incidents/')) return 'incidents';
  if (path.includes('/historical-jira/')) return 'historical-jira';
  if (path.includes('/historical-pr/')) return 'historical-pr';
  if (path.includes('/testing/')) return 'testing';
  if (path.includes('/concepts/')) return 'concepts';
  if (path.includes('/domain/')) return 'domain';
  if (/\.(java|ts|py|tsx|jsx)$/i.test(sourcePath)) return 'code';
  return 'api';
}

function componentFromPath(sourcePath: string, fallback: string): string {
  const path = sourcePath.toLowerCase();
  if (path.includes('output')) return 'output-collection';
  if (path.includes('status') || path.includes('execution')) return 'job-execution';
  if (path.includes('batch')) return 'batch-job';
  return fallback;
}

function conceptsFromPath(sourcePath: string): string[] {
  const path = sourcePath.toLowerCase();
  const concepts: string[] = [];
  if (path.includes('output')) concepts.push('output collection');
  if (path.includes('status')) concepts.push('status tracking');
  if (path.includes('execution')) concepts.push('job execution');
  if (path.includes('idempot')) concepts.push('idempotency');
  if (path.includes('test')) concepts.push('test coverage');
  return concepts;
}
