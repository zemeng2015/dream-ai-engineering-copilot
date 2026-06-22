// SPDX-License-Identifier: Apache-2.0

export type WorkflowType =
  | 'requirement_draft'
  | 'requirement_case'
  | 'engineering_brief'
  | 'jira_draft'
  | 'pr_review_summary'
  | 'knowledge_search'
  | 'codebase_index'
  | 'evidence_graph'
  | 'testgen_stub'
  | 'audit_eval'
  | 'eval_scorecard';

export type RunStatus = 'success' | 'completed' | 'needs_review' | 'warning' | 'failed' | 'stub_only';

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

export interface ImpactItem {
  areaType: 'frontend' | 'backend' | 'api' | 'data' | 'workflow' | 'test' | 'ops' | 'security';
  name: string;
  description: string;
  confidence: number;
  sources: string[];
  reason: string;
}

export interface ClarificationQuestion {
  targetRole: 'BA' | 'TL' | 'FE' | 'BE' | 'QA' | 'OPS' | 'SECURITY';
  question: string;
  whyItMatters: string;
  relatedSources: string[];
}

export interface RequirementCase {
  caseId: string;
  title: string;
  rawRequest: string;
  createdByRole: string;
  status: 'created' | 'analyzed' | 'brief_generated' | 'closed';
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

export interface EvaluationScorecard {
  evaluationId: string;
  targetType: 'requirement_case' | 'engineering_brief' | 'jira_draft' | 'pr_review' | 'testgen_report';
  targetId: string;
  overallScore: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  passStatus: 'pass' | 'warning' | 'fail';
  sourceCoverage: Record<string, boolean>;
  dimensions: EvaluationDimension[];
  missingCriticalItems: string[];
  recommendations: string[];
}

export interface AuditRun {
  runId: string;
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
