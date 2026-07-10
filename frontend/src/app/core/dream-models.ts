// SPDX-License-Identifier: Apache-2.0

export type WorkflowType =
  | 'requirement_draft'
  | 'requirement_case'
  | 'requirement_case_create'
  | 'requirement_case_analysis'
  | 'requirement_question_answer'
  | 'requirement_question_waive'
  | 'engineering_brief'
  | 'jira_draft_context'
  | 'jira_draft'
  | 'jira_readiness_check'
  | 'pr_review_summary'
  | 'knowledge_search'
  | 'knowledge_intake'
  | 'knowledge_intake_upload'
  | 'knowledge_intake_parse'
  | 'knowledge_intake_metadata_update'
  | 'knowledge_intake_review'
  | 'knowledge_intake_promote'
  | 'context_intelligence'
  | 'retrieval_context_eval'
  | 'codebase_index'
  | 'evidence_graph'
  | 'testgen_stub'
  | 'audit_eval'
  | 'evaluation_scorecard'
  | 'eval_scorecard'
  | 'llm_judge_eval';

export type RunStatus =
  | 'success'
  | 'completed'
  | 'created'
  | 'answered'
  | 'waived'
  | 'uploaded'
  | 'parsed'
  | 'approved'
  | 'promoted'
  | 'needs_review'
  | 'pending_review'
  | 'warning'
  | 'failed'
  | 'fail'
  | 'pass'
  | 'stub_only'
  | 'jira_draft_needs_answers'
  | 'jira_ready_draft';

export type EvidenceSourceType =
  | 'domain_doc'
  | 'architecture_doc'
  | 'runbook'
  | 'incident'
  | 'historical_jira'
  | 'historical_pr'
  | 'testing_doc'
  | 'concept_memory'
  | 'graph_evidence'
  | 'code_file'
  | 'test_file';

export interface KnowledgePack {
  id: string;
  name: string;
  app: string;
  component: string;
  docType: string;
  status: 'Healthy' | 'Warning' | 'Critical';
  coverage: number;
  updatedAt: string;
}

export interface KnowledgeChunk {
  id: string;
  title: string;
  sourcePath: string;
  excerpt: string;
  concepts: string[];
  sourceType: EvidenceSourceType;
  metadata: {
    teamId: string;
    app: string;
    component: string;
    docType: string;
  };
}

export type KnowledgeIntakeSourceKind = 'runbook' | 'docx' | 'confluence_hld';

export type KnowledgeIntakeQueueStatus = 'queued' | 'parsing' | 'parsed' | 'ready_for_review' | 'promoted';

export type KnowledgeIntakeReviewStatus = 'unreviewed' | 'needs_review' | 'approved' | 'promoted';

export interface KnowledgeIntakeSection {
  id: string;
  heading: string;
  summary: string;
  concepts: string[];
  confidence: number;
}

export interface KnowledgeIntakeItem {
  id: string;
  title: string;
  sourceKind: KnowledgeIntakeSourceKind;
  sourcePath: string;
  owner: string;
  importedAt: string;
  queueStatus: KnowledgeIntakeQueueStatus;
  reviewStatus: KnowledgeIntakeReviewStatus;
  targetPack: string;
  parser: string;
  parsedConcepts: string[];
  sections: KnowledgeIntakeSection[];
  reviewNotes: string[];
  promotionSummary: string;
}

export interface CodebaseFile {
  id: string;
  path: string;
  layer: 'frontend' | 'backend' | 'aws' | 'python' | 'test';
  language: 'typescript' | 'java' | 'python' | 'json' | 'markdown';
  role: 'source' | 'test' | 'config' | 'docs';
  summary: string;
  concepts: string[];
  symbols: string[];
  relatedTests: string[];
}

export interface EvidenceGraphNode {
  id: string;
  type:
    | 'concept'
    | 'domain_doc'
    | 'architecture_doc'
    | 'incident'
    | 'historical_jira'
    | 'historical_pr'
    | 'code_file'
    | 'test_file'
    | 'runbook';
  title: string;
  sourcePath: string;
  concepts: string[];
  summary: string;
}

export interface EvidenceGraphPath {
  id: string;
  concept: string;
  path: string[];
  evidenceTypes: EvidenceGraphNode['type'][];
  risk: string;
  reviewHint: string;
}

export interface ContextEvidence {
  evidenceId: string;
  title: string;
  sourcePath: string;
  sourceType: EvidenceSourceType;
  excerpt: string;
  relevanceScore: number;
  reason: string;
}

export type ContextIntelligenceStatus = 'pass' | 'watch' | 'needs_review';

export interface ContextRetrievalTrailItem {
  id: string;
  step: number;
  label: string;
  detail: string;
  query: string;
  sourcesMatched: number;
  status: ContextIntelligenceStatus;
}

export interface ContextPackSection {
  id: string;
  title: string;
  summary: string;
  includedEvidenceIds: string[];
  tokenEstimate: number;
  guardrail: string;
  status: ContextIntelligenceStatus;
}

export interface ContextPromptPreview {
  system: string;
  developer: string;
  user: string;
  evidenceInstructions: string[];
}

export interface RetrievalEvalMetric {
  label: string;
  value: string;
  target: string;
  status: ContextIntelligenceStatus;
  note: string;
}

export interface LogicChainStep {
  id: string;
  order: number;
  title: string;
  input: string;
  output: string;
  evidenceIds: string[];
  status: ContextIntelligenceStatus;
}

export interface ContextIntelligenceSnapshot {
  caseId: string;
  title: string;
  request: string;
  retrievalTrail: ContextRetrievalTrailItem[];
  contextPackSections: ContextPackSection[];
  promptPreview: ContextPromptPreview;
  metrics: RetrievalEvalMetric[];
  evidenceCards: ContextEvidence[];
  logicChain: LogicChainStep[];
}

export interface ImpactItem {
  areaType: 'frontend' | 'backend' | 'api' | 'data' | 'workflow' | 'test' | 'ops' | 'security';
  name: string;
  description: string;
  confidence: number;
  sources: string[];
  reason: string;
}

export interface ClarificationQuestion {
  questionId: string;
  targetRole: 'BA' | 'TL' | 'FE' | 'BE' | 'QA' | 'OPS' | 'SECURITY';
  question: string;
  whyItMatters: string;
  relatedSources: string[];
  status: 'open' | 'answered' | 'waived';
  answer?: string;
  answeredBy?: string;
  answeredAt?: string;
  waivedReason?: string;
  waivedBy?: string;
  waivedAt?: string;
}

export interface RequirementCase {
  caseId: string;
  title: string;
  rawRequest: string;
  createdByRole: string;
  status:
    | 'created'
    | 'analyzed'
    | 'brief_generated'
    | 'questions_answered'
    | 'jira_draft_needs_answers'
    | 'jira_ready_draft'
    | 'closed';
  jiraReadinessStatus?: 'jira_draft_needs_answers' | 'jira_ready_draft';
  jiraReady?: boolean;
  confidence: number;
  createdAt: string;
  updatedAt: string;
  evidence: ContextEvidence[];
  impactMap: ImpactItem[];
  questions: ClarificationQuestion[];
  engineeringBrief: string;
  jiraDraft: string;
}

export interface EvaluationDimension {
  name: string;
  score: number;
  weight: number;
  passed: boolean;
  rationale: string;
  evidence: string[];
  missingItems: string[];
  recommendations: string[];
}

export interface LLMJudgeResult {
  status: 'completed' | 'failed';
  provider?: string;
  model?: string;
  promptVersion: string;
  inputHash?: string;
  durationMs?: number;
  readiness?: string;
  confidence?: number;
  summary?: string;
  risks: string[];
  missingEvidence: string[];
  recommendations: string[];
  warning?: string;
}

export interface EvaluationScorecard {
  evaluationId: string;
  targetType: 'requirement_case' | 'engineering_brief' | 'jira_draft' | 'pr_review' | 'testgen_report';
  targetId: string;
  caseId?: string;
  runId?: string;
  teamId?: string;
  outputPath?: string;
  overallScore: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  passStatus: 'pass' | 'warning' | 'fail';
  sourceCoverage: Record<string, boolean>;
  dimensions: EvaluationDimension[];
  missingCriticalItems: string[];
  hallucinationWarnings?: string[];
  recommendations: string[];
  llmJudge?: LLMJudgeResult;
}

export interface AuditRun {
  runId: string;
  caseId?: string | null;
  useCase: WorkflowType;
  teamId: string;
  app: string;
  status: RunStatus;
  startedAt: string;
  duration: string;
  modelProvider: string;
  modelName: string;
  outputPath: string;
  warnings: string[];
  sourcesUsed: string[];
}

export interface HumanRating {
  runId: string;
  usefulnessScore: number;
  correctnessScore: number;
  comments: string;
  createdAt: string;
}

export interface RequirementDraftInput {
  teamId: string;
  app: string;
  component: string;
  roughBusinessRequest: string;
  topK: number;
  role?: string;
  userId?: string;
  sessionId?: string;
  experienceTokenBudget?: number;
}

export interface RequirementDraftResult {
  run: AuditRun;
  markdown: string;
  sourcesUsed: KnowledgeChunk[];
  warnings: string[];
  requirementCase: RequirementCase;
  scorecard: EvaluationScorecard;
}

export interface PrReviewInput {
  teamId: string;
  app: string;
  component: string;
  diffText: string;
  jiraContext: string;
  topK: number;
}

export interface PrReviewResult {
  run: AuditRun;
  markdown: string;
  risk: 'Low' | 'Medium' | 'High';
  sourcesUsed: KnowledgeChunk[];
  warnings: string[];
  changedFiles: string[];
  relatedCode: CodebaseFile[];
  scorecard: EvaluationScorecard;
}

export interface TestGenStubInput {
  teamId: string;
  repoPath: string;
  targetLanguage: string;
  dryRun: boolean;
}

export interface TestGenStubPlan {
  runId: string;
  providerName: 'mock' | 'jtestgen-stub';
  targetSummary: string;
  plannedActions: string[];
  warnings: string[];
}

export interface TestGenStubResult {
  run: AuditRun;
  status: 'stub_only';
  reportMarkdown: string;
  generatedFiles: string[];
  warnings: string[];
  scorecard: EvaluationScorecard;
}
