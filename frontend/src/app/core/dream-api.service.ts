// SPDX-License-Identifier: Apache-2.0

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, defer, map, of, switchMap, tap } from 'rxjs';

import {
  AuditRun,
  ClarificationQuestion,
  CodebaseFile,
  ContextEvidence,
  EvaluationDimension,
  EvaluationScorecard,
  EvidenceSourceType,
  HumanRating,
  ImpactItem,
  KnowledgeChunk,
  LLMJudgeResult,
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

interface ApiHealthResponse {
  status: string;
  service: string;
  track: string;
  deployment_target: string;
  alibaba_cloud_region?: string | null;
  alibaba_cloud_service?: string | null;
  llm_provider: string;
  llm_model?: string | null;
  llm_base_url?: string | null;
  llm_api_key_configured: boolean;
  proof_file: string;
}

interface ApiQwenCloudShowcaseRuntime {
  status: string;
  service: string;
  track: string;
  deployment_target: string;
  alibaba_cloud_region?: string | null;
  alibaba_cloud_service?: string | null;
  llm_provider: string;
  llm_model?: string | null;
  llm_api_key_configured: boolean;
  proof_file: string;
  qwen_cloud_ready: boolean;
  alibaba_runtime_ready: boolean;
  live_backend_ready: boolean;
}

interface ApiQwenCloudShowcaseStep {
  order: string;
  title: string;
  route: string;
  outcome: string;
  evidence_paths: string[];
}

interface ApiQwenCloudShowcaseEvidenceItem {
  name: string;
  state: string;
  proof_paths: string[];
}

interface ApiQwenCloudShowcaseScorecard {
  weighted_current_evidence_ready: number;
  weighted_static_evidence_ready: number;
  weighted_total: number;
  live_backend_points: number;
  public_video_points: number;
  missing_external_inputs: string[];
}

interface ApiQwenCloudShowcaseBenchmark {
  status: string;
  run_id?: string | null;
  provider?: string | null;
  model?: string | null;
  case_count: number;
  baseline_score: number;
  dream_score: number;
  score_delta: number;
  median_delta: number;
  exact_paired_permutation_p?: number | null;
  dream_wins: number;
  exact_retrieval_recall_at_12: number;
  report_path?: string | null;
  limitations: string[];
}

interface ApiQwenCloudExperienceBenchmark {
  status: string;
  run_id?: string | null;
  provider?: string | null;
  model?: string | null;
  case_count: number;
  decision_count: number;
  passed_cases: number;
  proposal_accuracy: number;
  action_accuracy: number;
  critical_memory_recall: number;
  forbidden_memory_leak_rate: number;
  token_budget_compliance: number;
  memory_payload_accuracy: number;
  exact_canonical_key_accuracy: number;
  overall_score: number;
  report_path?: string | null;
  limitations: string[];
}

interface ApiQwenCloudShowcaseResponse {
  generated_at: string;
  project_title: string;
  track: string;
  elevator_pitch: string;
  runtime: ApiQwenCloudShowcaseRuntime;
  judge_flow: ApiQwenCloudShowcaseStep[];
  evidence: ApiQwenCloudShowcaseEvidenceItem[];
  benchmark: ApiQwenCloudShowcaseBenchmark;
  experience_benchmark: ApiQwenCloudExperienceBenchmark;
  scorecard: ApiQwenCloudShowcaseScorecard;
}

interface ApiExperienceMemory {
  memory_id: string;
  team_id: string;
  user_id: string;
  kind: ExperienceMemoryKind;
  key: string;
  value: string;
  status: ExperienceMemoryStatus;
  confidence: number;
  importance: number;
  source_session_id: string;
  source_reference: string;
  created_at: string;
  updated_at: string;
  valid_from: string;
  valid_until?: string | null;
  superseded_by?: string | null;
  last_recalled_at?: string | null;
  recall_count: number;
  feedback_count: number;
  helpful_total: number;
  correctness_total: number;
}

interface ApiExperienceDecision {
  decision_id: string;
  team_id: string;
  user_id: string;
  session_id: string;
  requested_action: ExperienceMemoryAction;
  action: ExperienceMemoryAction;
  target_memory_id?: string | null;
  created_memory_id?: string | null;
  rationale: string;
  provider_name: string;
  model_name: string;
  token_usage?: Record<string, number> | null;
  created_at: string;
}

interface ApiExperienceCaptureResult {
  decision: ApiExperienceDecision;
  memory?: ApiExperienceMemory | null;
  affected_memories: ApiExperienceMemory[];
  active_memory_count: number;
}

interface ApiExperienceRecallCandidate {
  memory: ApiExperienceMemory;
  score: number;
  estimated_tokens: number;
  selected: boolean;
  reason: string;
}

interface ApiExperienceRecallResult {
  team_id: string;
  user_id: string;
  session_id: string;
  query: string;
  token_budget: number;
  estimated_tokens_used: number;
  selected: ApiExperienceRecallCandidate[];
  excluded: ApiExperienceRecallCandidate[];
  expired_memory_ids: string[];
  context_card: string;
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

interface ApiContextRetrievalStep {
  step_name: string;
  query: string;
  provider: string;
  candidates_found: number;
  selected_count: number;
  notes: string[];
}

interface ApiEvidenceCandidate {
  evidence_id: string;
  source_type: string;
  title: string;
  source_path: string;
  excerpt: string;
  score: number;
  reason: string;
  selected: boolean;
  excluded_reason?: string | null;
  concepts: string[];
  authority_status: string;
}

interface ApiMemoryIntakeSectionProof {
  section_id: string;
  heading: string;
  source_reference?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  section_hash?: string | null;
}

interface ApiMemoryIntakeProof {
  document_id: string;
  draft_id?: string | null;
  original_path?: string | null;
  stored_path?: string | null;
  promoted_path: string;
  source_hash?: string | null;
  source_hash_verified?: boolean | null;
  review_status?: string | null;
  match_explanation?: string | null;
  matched_terms?: string[];
  intake_audit_run_ids: string[];
  section_proofs: ApiMemoryIntakeSectionProof[];
}

interface ApiMemoryClaimReference {
  claim_id: string;
  status: string;
  entity: string;
  relation: string;
  value?: string | null;
  evidence_paths: string[];
  intake_proofs?: ApiMemoryIntakeProof[];
  reason: string;
}

interface ApiMemoryEntity {
  entity_id: string;
  entity_type: string;
  canonical_name: string;
  aliases: string[];
}

interface ApiMemoryRelation {
  type: string;
  object_entity_id?: string | null;
  value?: string | null;
  condition?: string | null;
}

interface ApiMemoryEvidenceSpan {
  source_id: string;
  source_type: string;
  path: string;
  commit_sha?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  excerpt_hash: string;
  span_id: string;
}

interface ApiMemoryEvidence {
  source_ids: string[];
  spans: ApiMemoryEvidenceSpan[];
  intake_proofs?: ApiMemoryIntakeProof[];
}

interface ApiExtractionInfo {
  method: string;
  extractor_version: string;
  model_name?: string | null;
  confidence: number;
}

interface ApiGovernanceInfo {
  status: string;
  risk_level: string;
  reviewer?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
}

interface ApiClaimAuditInfo {
  created_at: string;
  updated_at: string;
}

interface ApiMemoryClaim {
  claim_id: string;
  team_id: string;
  repo_id?: string | null;
  scan_id: string;
  entity: ApiMemoryEntity;
  relation: ApiMemoryRelation;
  evidence: ApiMemoryEvidence;
  extraction: ApiExtractionInfo;
  governance: ApiGovernanceInfo;
  audit: ApiClaimAuditInfo;
}

interface ApiMemoryDiffResult {
  team_id: string;
  scan_id: string;
  base_scan_id?: string | null;
  added_claims: ApiMemoryClaim[];
  removed_claims: ApiMemoryClaim[];
  changed_claims: ApiMemoryClaim[];
  unchanged_count: number;
  markdown: string;
}

interface ApiMemoryScanResult {
  scan_id: string;
  team_id: string;
  repo_name?: string | null;
  created_at: string;
  claims: ApiMemoryClaim[];
  summary: string;
  warnings: string[];
}

interface ApiMemoryReviewFieldDiff {
  field_path: string;
  before?: string | null;
  after?: string | null;
}

interface ApiMemoryReviewClaimSnapshot {
  claim_id: string;
  entity_type: string;
  entity_name: string;
  relation_type: string;
  relation_value?: string | null;
  extraction_method: string;
  confidence: number;
  risk_level: string;
  security_classification: string;
  evidence_paths: string[];
  intake_document_ids: string[];
  source_hashes: string[];
}

interface ApiMemoryReviewEvent {
  event_id: string;
  team_id: string;
  claim_id: string;
  scan_id: string;
  previous_status: string;
  new_status: string;
  reviewer?: string | null;
  reason?: string | null;
  reviewed_at: string;
  reviewer_signature?: string | null;
  field_diffs?: ApiMemoryReviewFieldDiff[];
  claim_snapshot?: ApiMemoryReviewClaimSnapshot | null;
  risk_signals?: string[];
  conflict_signals?: string[];
  signal_explanations?: ApiMemoryReviewSignalExplanation[];
}

interface ApiMemoryReviewSignalExplanation {
  signal: string;
  category: string;
  severity: string;
  explanation: string;
  evidence?: string[];
}

interface ApiMemoryLedgerSnapshot {
  team_id: string;
  updated_at: string;
  events: ApiMemoryReviewEvent[];
}

interface ApiMemoryConflictClaimSide {
  claim: ApiMemoryClaim;
  effective_status: string;
  relation_value?: string | null;
  evidence_paths?: string[];
  intake_document_ids?: string[];
  latest_review?: ApiMemoryReviewEvent | null;
}

interface ApiMemoryConflictPair {
  conflict_id: string;
  team_id: string;
  scan_id: string;
  entity_id: string;
  entity_name: string;
  entity_type: string;
  relation_type: string;
  left: ApiMemoryConflictClaimSide;
  right: ApiMemoryConflictClaimSide;
  signal: ApiMemoryReviewSignalExplanation;
}

interface ApiMemoryConflictReport {
  team_id: string;
  scan_id: string;
  generated_at: string;
  conflict_count: number;
  pairs: ApiMemoryConflictPair[];
}

interface ApiMemoryConflictResolutionEvent {
  event_id: string;
  team_id: string;
  scan_id: string;
  conflict_id: string;
  action: string;
  winning_claim_id: string;
  rejected_claim_id: string;
  reviewer?: string | null;
  reason?: string | null;
  resolved_at: string;
  reviewer_signature?: string | null;
  review_event_ids: string[];
  conflict_snapshot: ApiMemoryConflictPair;
}

interface ApiMemoryConflictResolutionLedger {
  team_id: string;
  updated_at: string;
  events: ApiMemoryConflictResolutionEvent[];
}

interface ApiGraphPathReference {
  query: string;
  path: string;
  source_paths: string[];
}

interface ApiContextRetrievalTrail {
  trail_id: string;
  run_id?: string | null;
  case_id?: string | null;
  review_id?: string | null;
  team_id: string;
  repo_name?: string | null;
  raw_query: string;
  detected_concepts: string[];
  retrieval_steps: ApiContextRetrievalStep[];
  candidate_evidence: ApiEvidenceCandidate[];
  selected_evidence: ApiEvidenceCandidate[];
  excluded_evidence: ApiEvidenceCandidate[];
  ranking_reasons: string[];
  graph_expansion_paths: ApiGraphPathReference[];
  memory_claims_considered: ApiMemoryClaimReference[];
  memory_claims_used: ApiMemoryClaimReference[];
  warnings: string[];
  final_context_summary: string;
  json_path?: string | null;
  markdown_path?: string | null;
}

interface ApiContextPack {
  context_pack_id: string;
  case_id?: string | null;
  run_id?: string | null;
  review_id?: string | null;
  team_id: string;
  repo_name?: string | null;
  user_request: string;
  selected_docs: ApiEvidenceCandidate[];
  selected_code: ApiEvidenceCandidate[];
  selected_tests: ApiEvidenceCandidate[];
  selected_incidents: ApiEvidenceCandidate[];
  selected_historical_jira: ApiEvidenceCandidate[];
  selected_historical_pr: ApiEvidenceCandidate[];
  selected_memory_claims: ApiMemoryClaimReference[];
  candidate_memory_claims: ApiMemoryClaimReference[];
  excluded_evidence: ApiEvidenceCandidate[];
  graph_paths: ApiGraphPathReference[];
  deterministic_size_budget: number;
  selected_evidence_count: number;
  warnings: string[];
  json_path?: string | null;
  markdown_path?: string | null;
}

interface ApiContextPromptPreview {
  preview_id: string;
  case_id?: string | null;
  run_id?: string | null;
  target: string;
  provider_mode: string;
  prompt_text: string;
  evidence_paths: string[];
  warnings: string[];
  json_path?: string | null;
  markdown_path?: string | null;
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
  waived_reason?: string | null;
  waived_by?: string | null;
  waived_at?: string | null;
}

interface ApiMarkdownArtifact {
  markdown: string;
  sources_used: string[];
  warnings: string[];
}

interface ApiJiraDraft extends ApiMarkdownArtifact {
  case_id: string;
}

interface ApiJiraDraftContext {
  case_id: string;
  deterministic_markdown: string;
  prompt: string;
  prompt_char_count: number;
  deterministic_char_count: number;
  sources_used: string[];
  warnings: string[];
}

interface ApiJiraReadiness {
  case_id: string;
  ready: boolean;
  status: string;
  answered_questions: number;
  waived_questions?: number;
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
  llm_judge?: ApiLLMJudgeResult | null;
  evaluated_artifact_path?: string | null;
  output_path?: string | null;
}

interface ApiLLMJudgeResult {
  status: string;
  provider?: string | null;
  model?: string | null;
  prompt_version: string;
  input_hash?: string | null;
  duration_ms?: number | null;
  readiness?: string | null;
  confidence?: number | null;
  summary?: string | null;
  risks: string[];
  missing_evidence: string[];
  recommendations: string[];
  warning?: string | null;
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

interface ApiHumanRating {
  run_id: string;
  usefulness_score: number;
  correctness_score: number;
  comments: string;
  created_at: string;
}

interface ApiIntakeDocument {
  document_id: string;
  team_id: string;
  title: string;
  document_type: string;
  original_path: string;
  stored_path: string;
  source_hash?: string | null;
  promoted_path?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  warnings: string[];
}

interface ApiIntakeConcept {
  concept: string;
  source_sections: string[];
  confidence: number;
}

interface ApiSourceSpan {
  start_line?: number | null;
  end_line?: number | null;
}

interface ApiParsedSection {
  section_id: string;
  heading: string;
  level: number;
  text: string;
  concepts: string[];
  source_reference?: string | null;
  source_span?: ApiSourceSpan | null;
  section_hash?: string | null;
}

interface ApiKnowledgeDraft {
  draft_id: string;
  document_id: string;
  team_id: string;
  title: string;
  target_doc_type: string;
  source_hash?: string | null;
  app?: string | null;
  component?: string | null;
  sections: ApiParsedSection[];
  concepts: ApiIntakeConcept[];
  review_status: string;
  reviewer?: string | null;
  review_notes?: string | null;
  promoted_path?: string | null;
  warnings: string[];
  json_path?: string | null;
  markdown_path?: string | null;
  normalized_markdown: string;
}

interface ApiDraftMetadataSnapshot {
  title: string;
  target_doc_type: string;
  app?: string | null;
  component?: string | null;
  concepts: string[];
  review_status: string;
  promoted_path?: string | null;
}

interface ApiDraftMetadataDiff {
  field: string;
  before?: unknown | null;
  after?: unknown | null;
}

interface ApiDraftReviewEvent {
  event_id: string;
  event_type: string;
  draft_id: string;
  document_id: string;
  team_id: string;
  created_at: string;
  reviewer?: string | null;
  notes?: string | null;
  previous_status: string;
  new_status: string;
  audit_run_id: string;
  metadata_snapshot: ApiDraftMetadataSnapshot;
  metadata_diff: ApiDraftMetadataDiff[];
  source_hash?: string | null;
  section_hashes: string[];
  warnings: string[];
}

interface ApiIntakeDocumentDetail {
  document: ApiIntakeDocument;
  draft?: ApiKnowledgeDraft | null;
  raw_text: string;
  raw_text_truncated: boolean;
  raw_size_bytes: number;
  raw_text_available: boolean;
  raw_text_warning?: string | null;
  source_hash_verified?: boolean | null;
  audit_events: ApiAuditRecord[];
  review_events: ApiDraftReviewEvent[];
  downstream_events: ApiAuditRecord[];
  downstream_usages: ApiDownstreamUsage[];
}

interface ApiDownstreamUsage {
  audit_record: ApiAuditRecord;
  matched_source_paths: string[];
  match_reason: string;
  detail_route?: string | null;
  match_proofs: ApiSourceMatchProof[];
}

interface ApiSectionMatchProof {
  section_id: string;
  heading: string;
  source_reference?: string | null;
  source_span?: ApiSourceSpan | null;
  section_hash?: string | null;
}

interface ApiSourceMatchProof {
  retrieved_source_path: string;
  matched_path: string;
  matched_label: string;
  document_id: string;
  draft_id?: string | null;
  source_hash?: string | null;
  source_hash_verified?: boolean | null;
  section_proofs: ApiSectionMatchProof[];
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
  sourceHash?: string | null;
  promotedPath?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
  warnings: string[];
}

export interface IntakeConcept {
  concept: string;
  sourceSections: string[];
  confidence: number;
}

export interface SourceSpan {
  startLine?: number | null;
  endLine?: number | null;
}

export interface ParsedSection {
  sectionId: string;
  heading: string;
  level: number;
  text: string;
  concepts: string[];
  sourceReference?: string | null;
  sourceSpan?: SourceSpan | null;
  sectionHash?: string | null;
}

export interface KnowledgeDraft {
  draftId: string;
  documentId: string;
  teamId: string;
  title: string;
  targetDocType: string;
  sourceHash?: string | null;
  app?: string | null;
  component?: string | null;
  sections: ParsedSection[];
  concepts: IntakeConcept[];
  reviewStatus: string;
  reviewer?: string | null;
  reviewNotes?: string | null;
  promotedPath?: string | null;
  warnings: string[];
  jsonPath?: string | null;
  markdownPath?: string | null;
  normalizedMarkdown: string;
}

export interface DraftMetadataSnapshot {
  title: string;
  targetDocType: string;
  app?: string | null;
  component?: string | null;
  concepts: string[];
  reviewStatus: string;
  promotedPath?: string | null;
}

export interface DraftMetadataDiff {
  field: string;
  before?: unknown | null;
  after?: unknown | null;
}

export interface DraftReviewEvent {
  eventId: string;
  eventType: string;
  draftId: string;
  documentId: string;
  teamId: string;
  createdAt: string;
  reviewer?: string | null;
  notes?: string | null;
  previousStatus: string;
  newStatus: string;
  auditRunId: string;
  metadataSnapshot: DraftMetadataSnapshot;
  metadataDiff: DraftMetadataDiff[];
  sourceHash?: string | null;
  sectionHashes: string[];
  warnings: string[];
}

export interface IntakeDocumentDetail {
  document: IntakeDocument;
  draft?: KnowledgeDraft | null;
  rawText: string;
  rawTextTruncated: boolean;
  rawSizeBytes: number;
  rawTextAvailable: boolean;
  rawTextWarning?: string | null;
  sourceHashVerified?: boolean | null;
  auditEvents: AuditRun[];
  reviewEvents: DraftReviewEvent[];
  downstreamEvents: AuditRun[];
  downstreamUsages: DownstreamUsage[];
}

export interface DownstreamUsage {
  auditRun: AuditRun;
  matchedSourcePaths: string[];
  matchReason: string;
  detailRoute?: string | null;
  matchProofs: SourceMatchProof[];
}

export interface SectionMatchProof {
  sectionId: string;
  heading: string;
  sourceReference?: string | null;
  sourceSpan?: SourceSpan | null;
  sectionHash?: string | null;
}

export interface SourceMatchProof {
  retrievedSourcePath: string;
  matchedPath: string;
  matchedLabel: string;
  documentId: string;
  draftId?: string | null;
  sourceHash?: string | null;
  sourceHashVerified?: boolean | null;
  sectionProofs: SectionMatchProof[];
}

export interface ContextRetrievalStep {
  stepName: string;
  query: string;
  provider: string;
  candidatesFound: number;
  selectedCount: number;
  notes: string[];
}

export interface ContextEvidenceCandidate {
  evidenceId: string;
  sourceType: string;
  title: string;
  sourcePath: string;
  excerpt: string;
  score: number;
  reason: string;
  selected: boolean;
  excludedReason?: string | null;
  concepts: string[];
  authorityStatus: string;
}

export interface ContextMemoryIntakeSectionProof {
  sectionId: string;
  heading: string;
  sourceReference?: string | null;
  startLine?: number | null;
  endLine?: number | null;
  sectionHash?: string | null;
}

export interface ContextMemoryIntakeProof {
  documentId: string;
  draftId?: string | null;
  originalPath?: string | null;
  storedPath?: string | null;
  promotedPath: string;
  sourceHash?: string | null;
  sourceHashVerified?: boolean | null;
  reviewStatus?: string | null;
  matchExplanation?: string | null;
  matchedTerms: string[];
  intakeAuditRunIds: string[];
  sectionProofs: ContextMemoryIntakeSectionProof[];
}

export interface ContextMemoryClaimReference {
  claimId: string;
  status: string;
  entity: string;
  relation: string;
  value?: string | null;
  evidencePaths: string[];
  intakeProofs: ContextMemoryIntakeProof[];
  reason: string;
}

export interface MemoryEntity {
  entityId: string;
  entityType: string;
  canonicalName: string;
  aliases: string[];
}

export interface MemoryRelation {
  type: string;
  objectEntityId?: string | null;
  value?: string | null;
  condition?: string | null;
}

export interface MemoryEvidenceSpan {
  sourceId: string;
  sourceType: string;
  path: string;
  commitSha?: string | null;
  startLine?: number | null;
  endLine?: number | null;
  excerptHash: string;
  spanId: string;
}

export interface MemoryEvidence {
  sourceIds: string[];
  spans: MemoryEvidenceSpan[];
  intakeProofs: ContextMemoryIntakeProof[];
}

export interface MemoryClaim {
  claimId: string;
  teamId: string;
  repoId?: string | null;
  scanId: string;
  entity: MemoryEntity;
  relation: MemoryRelation;
  evidence: MemoryEvidence;
  extractionMethod: string;
  extractorVersion: string;
  confidence: number;
  governanceStatus: string;
  riskLevel: string;
  createdAt: string;
  updatedAt: string;
}

export interface MemoryDiffResult {
  teamId: string;
  scanId: string;
  baseScanId?: string | null;
  addedClaims: MemoryClaim[];
  removedClaims: MemoryClaim[];
  changedClaims: MemoryClaim[];
  unchangedCount: number;
  markdown: string;
}

export interface MemoryScanResult {
  scanId: string;
  teamId: string;
  repoName?: string | null;
  createdAt: string;
  claims: MemoryClaim[];
  summary: string;
  warnings: string[];
}

export interface MemoryReviewEvent {
  eventId: string;
  teamId: string;
  claimId: string;
  scanId: string;
  previousStatus: string;
  newStatus: string;
  reviewer?: string | null;
  reason?: string | null;
  reviewedAt: string;
  reviewerSignature?: string | null;
  fieldDiffs: MemoryReviewFieldDiff[];
  claimSnapshot?: MemoryReviewClaimSnapshot | null;
  riskSignals: string[];
  conflictSignals: string[];
  signalExplanations: MemoryReviewSignalExplanation[];
}

export interface MemoryReviewFieldDiff {
  fieldPath: string;
  before?: string | null;
  after?: string | null;
}

export interface MemoryReviewClaimSnapshot {
  claimId: string;
  entityType: string;
  entityName: string;
  relationType: string;
  relationValue?: string | null;
  extractionMethod: string;
  confidence: number;
  riskLevel: string;
  securityClassification: string;
  evidencePaths: string[];
  intakeDocumentIds: string[];
  sourceHashes: string[];
}

export interface MemoryReviewSignalExplanation {
  signal: string;
  category: string;
  severity: string;
  explanation: string;
  evidence: string[];
}

export interface MemoryLedgerSnapshot {
  teamId: string;
  updatedAt: string;
  events: MemoryReviewEvent[];
}

export interface MemoryConflictClaimSide {
  claim: MemoryClaim;
  effectiveStatus: string;
  relationValue?: string | null;
  evidencePaths: string[];
  intakeDocumentIds: string[];
  latestReview?: MemoryReviewEvent | null;
}

export interface MemoryConflictPair {
  conflictId: string;
  teamId: string;
  scanId: string;
  entityId: string;
  entityName: string;
  entityType: string;
  relationType: string;
  left: MemoryConflictClaimSide;
  right: MemoryConflictClaimSide;
  signal: MemoryReviewSignalExplanation;
}

export interface MemoryConflictReport {
  teamId: string;
  scanId: string;
  generatedAt: string;
  conflictCount: number;
  pairs: MemoryConflictPair[];
}

export interface MemoryConflictResolutionEvent {
  eventId: string;
  teamId: string;
  scanId: string;
  conflictId: string;
  action: string;
  winningClaimId: string;
  rejectedClaimId: string;
  reviewer?: string | null;
  reason?: string | null;
  resolvedAt: string;
  reviewerSignature?: string | null;
  reviewEventIds: string[];
  conflictSnapshot: MemoryConflictPair;
}

export interface MemoryConflictResolutionLedger {
  teamId: string;
  updatedAt: string;
  events: MemoryConflictResolutionEvent[];
}

export interface ContextGraphPathReference {
  query: string;
  path: string;
  sourcePaths: string[];
}

export interface ContextRetrievalTrail {
  trailId: string;
  runId?: string | null;
  caseId?: string | null;
  reviewId?: string | null;
  teamId: string;
  repoName?: string | null;
  rawQuery: string;
  detectedConcepts: string[];
  retrievalSteps: ContextRetrievalStep[];
  candidateEvidence: ContextEvidenceCandidate[];
  selectedEvidence: ContextEvidenceCandidate[];
  excludedEvidence: ContextEvidenceCandidate[];
  rankingReasons: string[];
  graphExpansionPaths: ContextGraphPathReference[];
  memoryClaimsConsidered: ContextMemoryClaimReference[];
  memoryClaimsUsed: ContextMemoryClaimReference[];
  warnings: string[];
  finalContextSummary: string;
  jsonPath?: string | null;
  markdownPath?: string | null;
}

export interface ContextPack {
  contextPackId: string;
  caseId?: string | null;
  runId?: string | null;
  reviewId?: string | null;
  teamId: string;
  repoName?: string | null;
  userRequest: string;
  selectedDocs: ContextEvidenceCandidate[];
  selectedCode: ContextEvidenceCandidate[];
  selectedTests: ContextEvidenceCandidate[];
  selectedIncidents: ContextEvidenceCandidate[];
  selectedHistoricalJira: ContextEvidenceCandidate[];
  selectedHistoricalPr: ContextEvidenceCandidate[];
  selectedMemoryClaims: ContextMemoryClaimReference[];
  candidateMemoryClaims: ContextMemoryClaimReference[];
  excludedEvidence: ContextEvidenceCandidate[];
  graphPaths: ContextGraphPathReference[];
  deterministicSizeBudget: number;
  selectedEvidenceCount: number;
  warnings: string[];
  jsonPath?: string | null;
  markdownPath?: string | null;
}

export interface ContextPromptPreview {
  previewId: string;
  caseId?: string | null;
  runId?: string | null;
  target: string;
  providerMode: string;
  promptText: string;
  evidencePaths: string[];
  warnings: string[];
  jsonPath?: string | null;
  markdownPath?: string | null;
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

export type RequirementDraftLifecycleStepId =
  | 'create_case'
  | 'analyze_evidence'
  | 'prepare_jira_context'
  | 'draft_jira'
  | 'readiness_check'
  | 'eval_score'
  | 'llm_judge'
  | 'load_result';

export interface RequirementDraftLifecycleProgress {
  stepId: RequirementDraftLifecycleStepId;
  state: 'start' | 'complete';
  durationMs?: number;
}

export interface DreamHealth {
  status: string;
  service: string;
  track: string;
  deploymentTarget: string;
  alibabaCloudRegion: string | null;
  alibabaCloudService: string | null;
  llmProvider: string;
  llmModel: string | null;
  llmBaseUrl: string | null;
  llmApiKeyConfigured: boolean;
  proofFile: string;
}

export interface QwenCloudShowcaseRuntime {
  status: string;
  service: string;
  track: string;
  deploymentTarget: string;
  alibabaCloudRegion: string | null;
  alibabaCloudService: string | null;
  llmProvider: string;
  llmModel: string | null;
  llmApiKeyConfigured: boolean;
  proofFile: string;
  qwenCloudReady: boolean;
  alibabaRuntimeReady: boolean;
  liveBackendReady: boolean;
}

export interface QwenCloudShowcaseStep {
  order: string;
  title: string;
  route: string;
  outcome: string;
  evidencePaths: string[];
}

export interface QwenCloudShowcaseEvidenceItem {
  name: string;
  state: string;
  proofPaths: string[];
}

export interface QwenCloudShowcaseScorecard {
  weightedCurrentEvidenceReady: number;
  weightedStaticEvidenceReady: number;
  weightedTotal: number;
  liveBackendPoints: number;
  publicVideoPoints: number;
  missingExternalInputs: string[];
}

export interface QwenCloudShowcaseBenchmark {
  status: string;
  runId: string | null;
  provider: string | null;
  model: string | null;
  caseCount: number;
  baselineScore: number;
  dreamScore: number;
  scoreDelta: number;
  medianDelta: number;
  exactPairedPermutationP: number | null;
  dreamWins: number;
  exactRetrievalRecallAt12: number;
  reportPath: string | null;
  limitations: string[];
}

export interface QwenCloudExperienceBenchmark {
  status: string;
  runId: string | null;
  provider: string | null;
  model: string | null;
  caseCount: number;
  curatorDecisionCount: number;
  lifecycleCasesPassed: number;
  lifecycleCasePassRate: number;
  proposalAccuracy: number;
  governedActionAccuracy: number;
  criticalMemoryRecall: number;
  forbiddenMemoryLeakRate: number;
  tokenBudgetCompliance: number;
  overallScore: number;
  reportPath: string | null;
  limitations: string[];
}

export type ExperienceMemoryKind = 'preference' | 'policy' | 'episode';
export type ExperienceMemoryStatus = 'active' | 'superseded' | 'expired' | 'forgotten';
export type ExperienceMemoryAction = 'remember' | 'supersede' | 'forget' | 'ignore';

export interface ExperienceMemory {
  memoryId: string;
  teamId: string;
  userId: string;
  kind: ExperienceMemoryKind;
  key: string;
  value: string;
  status: ExperienceMemoryStatus;
  confidence: number;
  importance: number;
  sourceSessionId: string;
  sourceReference: string;
  createdAt: string;
  updatedAt: string;
  validFrom: string;
  validUntil: string | null;
  supersededBy: string | null;
  lastRecalledAt: string | null;
  recallCount: number;
  feedbackCount: number;
  helpfulTotal: number;
  correctnessTotal: number;
}

export interface ExperienceDecision {
  decisionId: string;
  teamId: string;
  userId: string;
  sessionId: string;
  requestedAction: ExperienceMemoryAction;
  action: ExperienceMemoryAction;
  targetMemoryId: string | null;
  createdMemoryId: string | null;
  rationale: string;
  providerName: string;
  modelName: string;
  tokenUsage: Record<string, number> | null;
  createdAt: string;
}

export interface ExperienceCaptureInput {
  teamId: string;
  userId: string;
  sessionId: string;
  observation: string;
  sourceReference: string;
  llmProvider?: 'qwen-cloud' | 'deterministic';
}

export interface ExperienceCaptureResult {
  decision: ExperienceDecision;
  memory: ExperienceMemory | null;
  affectedMemories: ExperienceMemory[];
  activeMemoryCount: number;
}

export interface ExperienceRecallInput {
  teamId: string;
  userId: string;
  sessionId: string;
  query: string;
  tokenBudget: number;
  limit?: number;
}

export interface ExperienceRecallCandidate {
  memory: ExperienceMemory;
  score: number;
  estimatedTokens: number;
  selected: boolean;
  reason: string;
}

export interface ExperienceRecallResult {
  teamId: string;
  userId: string;
  sessionId: string;
  query: string;
  tokenBudget: number;
  estimatedTokensUsed: number;
  selected: ExperienceRecallCandidate[];
  excluded: ExperienceRecallCandidate[];
  expiredMemoryIds: string[];
  contextCard: string;
}

export interface QwenCloudShowcase {
  generatedAt: string;
  projectTitle: string;
  track: string;
  elevatorPitch: string;
  runtime: QwenCloudShowcaseRuntime;
  judgeFlow: QwenCloudShowcaseStep[];
  evidence: QwenCloudShowcaseEvidenceItem[];
  benchmark: QwenCloudShowcaseBenchmark;
  experienceBenchmark: QwenCloudExperienceBenchmark;
  scorecard: QwenCloudShowcaseScorecard;
}

function resolveApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000';
  }

  const runtimeWindow = window as Window & { __DREAM_API_BASE_URL__?: string };
  const configured = runtimeWindow.__DREAM_API_BASE_URL__?.trim();
  if (configured) {
    return configured.replace(/\/+$/, '');
  }

  const localHosts = new Set(['localhost', '127.0.0.1', '::1', '[::1]']);
  return localHosts.has(window.location.hostname)
    ? 'http://127.0.0.1:8000'
    : window.location.origin;
}

@Injectable({ providedIn: 'root' })
export class DreamApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = resolveApiBaseUrl();

  getHealth(): Observable<DreamHealth> {
    return this.http.get<ApiHealthResponse>(`${this.baseUrl}/health`).pipe(map(mapHealth));
  }

  getQwenCloudShowcase(): Observable<QwenCloudShowcase> {
    return this.http
      .get<ApiQwenCloudShowcaseResponse>(`${this.baseUrl}/qwencloud/showcase`)
      .pipe(map(mapQwenCloudShowcase));
  }

  captureExperience(input: ExperienceCaptureInput): Observable<ExperienceCaptureResult> {
    return this.http
      .post<ApiExperienceCaptureResult>(`${this.baseUrl}/experience/capture`, {
        team_id: input.teamId,
        user_id: input.userId,
        session_id: input.sessionId,
        observation: input.observation,
        source_reference: input.sourceReference,
        llm_provider: input.llmProvider ?? 'qwen-cloud',
      })
      .pipe(map(mapExperienceCaptureResult));
  }

  recallExperience(input: ExperienceRecallInput): Observable<ExperienceRecallResult> {
    return this.http
      .post<ApiExperienceRecallResult>(`${this.baseUrl}/experience/recall`, {
        team_id: input.teamId,
        user_id: input.userId,
        session_id: input.sessionId,
        query: input.query,
        token_budget: input.tokenBudget,
        limit: input.limit ?? 8,
      })
      .pipe(map(mapExperienceRecallResult));
  }

  rateExperienceMemory(
    memoryId: string,
    teamId: string,
    userId: string,
    helpful: boolean,
    correct: boolean,
  ): Observable<ExperienceMemory> {
    return this.http
      .post<ApiExperienceMemory>(`${this.baseUrl}/experience/feedback`, {
        team_id: teamId,
        user_id: userId,
        memory_id: memoryId,
        helpful,
        correct,
      })
      .pipe(map(mapExperienceMemory));
  }

  listExperienceMemories(teamId: string, userId: string): Observable<ExperienceMemory[]> {
    return this.http
      .get<ApiExperienceMemory[]>(`${this.baseUrl}/experience/memories`, {
        params: { team_id: teamId, user_id: userId, include_inactive: true },
      })
      .pipe(map((items) => items.map(mapExperienceMemory)));
  }

  listExperienceDecisions(teamId: string, userId: string): Observable<ExperienceDecision[]> {
    return this.http
      .get<ApiExperienceDecision[]>(`${this.baseUrl}/experience/decisions`, {
        params: { team_id: teamId, user_id: userId },
      })
      .pipe(map((items) => items.map(mapExperienceDecision)));
  }

  draftRequirementWithOpenAI(
    input: RequirementDraftInput,
    onProgress?: (progress: RequirementDraftLifecycleProgress) => void,
  ): Observable<RequirementDraftResult> {
    return this.trackRequirementStep(
      'create_case',
      this.http.post<ApiRequirementCaseSnapshot>(`${this.baseUrl}/requirement-cases`, {
          team_id: input.teamId,
          raw_request: input.roughBusinessRequest,
          created_by_role: input.role || 'BA',
          target_app: input.app,
          target_component: input.component,
          user_id: input.userId || 'demo-reviewer',
          session_id: input.sessionId || `ui-${Date.now()}`,
          experience_token_budget: input.experienceTokenBudget || 512,
        }),
      onProgress,
    )
      .pipe(
        switchMap((snapshot) =>
          this.trackRequirementStep(
            'analyze_evidence',
            this.http.post<ApiRequirementCaseSnapshot>(
              `${this.baseUrl}/requirement-cases/${snapshot.case.case_id}/analyze`,
              {},
            ),
            onProgress,
          ),
        ),
        switchMap((snapshot) =>
          this.generateAndEvaluateRequirementCase(input, snapshot.case.case_id, onProgress),
        ),
      );
  }

  regenerateRequirementCaseWithOpenAI(
    input: RequirementDraftInput,
    caseId: string,
    onProgress?: (progress: RequirementDraftLifecycleProgress) => void,
  ): Observable<RequirementDraftResult> {
    return this.generateAndEvaluateRequirementCase(input, caseId, onProgress);
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

  waiveRequirementQuestion(
    caseId: string,
    questionId: string,
    reason: string,
  ): Observable<ClarificationQuestion> {
    return this.http
      .post<ApiClarificationQuestion>(
        `${this.baseUrl}/requirement-cases/${caseId}/questions/${questionId}/waive`,
        {
          reason,
          waived_by: 'Demo Reviewer',
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

  getContextTrail(caseId: string): Observable<ContextRetrievalTrail> {
    return this.http
      .get<ApiContextRetrievalTrail>(`${this.baseUrl}/context/trails/${caseId}`)
      .pipe(map(mapContextRetrievalTrail));
  }

  getContextPack(caseId: string): Observable<ContextPack> {
    return this.http
      .get<ApiContextPack>(`${this.baseUrl}/context/packs/${caseId}`)
      .pipe(map(mapContextPack));
  }

  getContextPromptPreview(caseId: string, target = 'jira_draft'): Observable<ContextPromptPreview> {
    return this.http
      .get<ApiContextPromptPreview>(`${this.baseUrl}/context/prompt-preview/${caseId}`, {
        params: { target },
      })
      .pipe(map(mapContextPromptPreview));
  }

  scanMemory(input: {
    teamId: string;
    repoPath: string;
    repoName?: string;
  }): Observable<MemoryScanResult> {
    return this.http
      .post<ApiMemoryScanResult>(`${this.baseUrl}/memory/scan`, {
        team_id: input.teamId,
        repo_path: input.repoPath,
        repo_name: input.repoName || null,
      })
      .pipe(map(mapMemoryScanResult));
  }

  getLatestMemoryScan(teamId: string): Observable<MemoryScanResult> {
    return this.http
      .get<ApiMemoryScanResult>(`${this.baseUrl}/memory/scans/latest`, {
        params: { team_id: teamId },
      })
      .pipe(map(mapMemoryScanResult));
  }

  getMemoryDiff(
    teamId: string,
    scanId = 'latest',
    baseScanId?: string,
  ): Observable<MemoryDiffResult> {
    return this.http
      .get<ApiMemoryDiffResult>(`${this.baseUrl}/memory/diff`, {
        params: {
          team_id: teamId,
          scan_id: scanId,
          ...(baseScanId ? { base_scan_id: baseScanId } : {}),
        },
      })
      .pipe(map(mapMemoryDiffResult));
  }

  getMemoryConflicts(teamId: string, scanId = 'latest'): Observable<MemoryConflictReport> {
    return this.http
      .get<ApiMemoryConflictReport>(`${this.baseUrl}/memory/conflicts`, {
        params: { team_id: teamId, scan_id: scanId },
      })
      .pipe(map(mapMemoryConflictReport));
  }

  getMemoryConflictResolutions(teamId: string): Observable<MemoryConflictResolutionLedger> {
    return this.http
      .get<ApiMemoryConflictResolutionLedger>(`${this.baseUrl}/memory/conflict-resolutions`, {
        params: { team_id: teamId },
      })
      .pipe(map(mapMemoryConflictResolutionLedger));
  }

  resolveMemoryConflict(input: {
    teamId: string;
    conflictId: string;
    winningClaimId: string;
    action?: string;
    reviewer?: string;
    reason?: string;
    scanId?: string;
  }): Observable<MemoryConflictResolutionEvent> {
    return this.http
      .post<ApiMemoryConflictResolutionEvent>(`${this.baseUrl}/memory/conflicts/resolve`, {
        team_id: input.teamId,
        conflict_id: input.conflictId,
        winning_claim_id: input.winningClaimId,
        action: input.action || 'approve_winner_reject_other',
        reviewer: input.reviewer || null,
        reason: input.reason || null,
        scan_id: input.scanId || 'latest',
      })
      .pipe(map(mapMemoryConflictResolutionEvent));
  }

  getMemoryLedger(teamId: string): Observable<MemoryLedgerSnapshot> {
    return this.http
      .get<ApiMemoryLedgerSnapshot>(`${this.baseUrl}/memory/ledger`, {
        params: { team_id: teamId },
      })
      .pipe(map(mapMemoryLedgerSnapshot));
  }

  reviewMemoryClaim(input: {
    teamId: string;
    claimId: string;
    status: string;
    reviewer?: string;
    reason?: string;
    scanId?: string;
  }): Observable<MemoryReviewEvent> {
    return this.http
      .post<ApiMemoryReviewEvent>(`${this.baseUrl}/memory/review`, {
        team_id: input.teamId,
        claim_id: input.claimId,
        status: input.status,
        reviewer: input.reviewer || null,
        reason: input.reason || null,
        scan_id: input.scanId || 'latest',
      })
      .pipe(map(mapMemoryReviewEvent));
  }

  listAuditRuns(defaultApp = 'Demo'): Observable<AuditRun[]> {
    return this.http
      .get<ApiAuditRecord[]>(`${this.baseUrl}/audit/runs`)
      .pipe(map((records) => records.map((record) => mapAuditRun(record, defaultApp))));
  }

  listHumanRatings(runId: string): Observable<HumanRating[]> {
    return this.http
      .get<ApiHumanRating[]>(`${this.baseUrl}/audit/runs/${runId}/ratings`)
      .pipe(map((ratings) => ratings.map(mapHumanRating)));
  }

  rateAuditRun(input: {
    runId: string;
    usefulnessScore: number;
    correctnessScore: number;
    comments: string;
  }): Observable<HumanRating> {
    return this.http
      .post<ApiHumanRating>(`${this.baseUrl}/audit/runs/${input.runId}/ratings`, {
        usefulness_score: input.usefulnessScore,
        correctness_score: input.correctnessScore,
        comments: input.comments,
      })
      .pipe(map(mapHumanRating));
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

  uploadIntakeFile(input: {
    teamId: string;
    file: File;
    documentType: string;
    title?: string;
  }): Observable<IntakeDocument> {
    const formData = new FormData();
    formData.append('team_id', input.teamId);
    formData.append('document_type', input.documentType);
    if (input.title?.trim()) {
      formData.append('title', input.title.trim());
    }
    formData.append('file', input.file, input.file.name);
    return this.http
      .post<ApiIntakeDocument>(`${this.baseUrl}/intake/documents/upload`, formData)
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

  getIntakeDraft(documentId: string): Observable<KnowledgeDraft> {
    return this.http
      .get<ApiKnowledgeDraft>(`${this.baseUrl}/intake/drafts/draft-${documentId}`)
      .pipe(map(mapKnowledgeDraft));
  }

  getIntakeDocumentDetail(documentId: string): Observable<IntakeDocumentDetail> {
    return this.http
      .get<ApiIntakeDocumentDetail>(`${this.baseUrl}/intake/documents/${documentId}/detail`)
      .pipe(map(mapIntakeDocumentDetail));
  }

  updateIntakeDraftMetadata(
    documentId: string,
    input: {
      title: string;
      targetDocType: string;
      app?: string;
      component?: string;
      concepts: string[];
      reviewer?: string;
      notes?: string;
    },
  ): Observable<KnowledgeDraft> {
    return this.http
      .patch<ApiKnowledgeDraft>(`${this.baseUrl}/intake/drafts/draft-${documentId}/metadata`, {
        title: input.title,
        target_doc_type: input.targetDocType,
        app: input.app || null,
        component: input.component || null,
        concepts: input.concepts,
        reviewer: input.reviewer || null,
        notes: input.notes || null,
      })
      .pipe(map(mapKnowledgeDraft));
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
        llm_provider: 'qwen-cloud',
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
    onProgress?: (progress: RequirementDraftLifecycleProgress) => void,
  ): Observable<RequirementDraftResult> {
    return this.trackRequirementStep(
      'prepare_jira_context',
      this.http.get<ApiJiraDraftContext>(
        `${this.baseUrl}/requirement-cases/${caseId}/jira-draft-context`,
      ),
      onProgress,
    )
      .pipe(
        switchMap(() =>
          this.trackRequirementStep(
            'draft_jira',
            this.http.get<ApiJiraDraft>(
              `${this.baseUrl}/requirement-cases/${caseId}/jira-draft?llm_provider=qwen-cloud`,
            ),
            onProgress,
          ),
        ),
        switchMap(() =>
          this.trackRequirementStep(
            'readiness_check',
            this.http.get<ApiJiraReadiness>(
              `${this.baseUrl}/requirement-cases/${caseId}/jira-readiness`,
            ),
            onProgress,
          ),
        ),
        switchMap(() =>
          this.trackRequirementStep(
            'eval_score',
            this.http.post<ApiEvaluationResult>(`${this.baseUrl}/eval/run`, {
              target_type: 'jira_draft',
              case_id: caseId,
              team_id: input.teamId,
              strict: true,
              judge_provider: 'none',
            }),
            onProgress,
          ),
        ),
        switchMap((evaluation) =>
          this.trackRequirementStep(
            'llm_judge',
            this.http
              .post<ApiEvaluationResult>(
                `${this.baseUrl}/eval/runs/${evaluation.scorecard.evaluation_id}/judge`,
                { judge_provider: 'qwen-cloud' },
              )
              .pipe(catchError(() => of(evaluation))),
            onProgress,
          ),
        ),
        switchMap((evaluation) =>
          this.trackRequirementStep(
            'load_result',
            this.http.get<ApiRequirementCaseSnapshot>(`${this.baseUrl}/requirement-cases/${caseId}`).pipe(
              switchMap((snapshot) =>
                this.listAuditRuns(input.app).pipe(
                  map((runs) => ({ evaluation, snapshot, runs })),
                ),
              ),
            ),
            onProgress,
          ),
        ),
        map(({ evaluation, snapshot, runs }) =>
          this.toRequirementDraftResult(
            input,
            snapshot,
            mapScorecard(evaluation.scorecard),
            runs.find(
              (run) => run.caseId === caseId && run.useCase === 'jira_draft',
            ),
          ),
        ),
      );
  }

  private trackRequirementStep<T>(
    stepId: RequirementDraftLifecycleStepId,
    source: Observable<T>,
    onProgress?: (progress: RequirementDraftLifecycleProgress) => void,
  ): Observable<T> {
    return defer(() => {
      const startedAt = Date.now();
      onProgress?.({ stepId, state: 'start' });
      return source.pipe(
        tap({
          next: () =>
            onProgress?.({
              stepId,
              state: 'complete',
              durationMs: Date.now() - startedAt,
            }),
        }),
      );
    });
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

function mapHealth(response: ApiHealthResponse): DreamHealth {
  return {
    status: response.status,
    service: response.service,
    track: response.track,
    deploymentTarget: response.deployment_target,
    alibabaCloudRegion: response.alibaba_cloud_region ?? null,
    alibabaCloudService: response.alibaba_cloud_service ?? null,
    llmProvider: response.llm_provider,
    llmModel: response.llm_model ?? null,
    llmBaseUrl: response.llm_base_url ?? null,
    llmApiKeyConfigured: response.llm_api_key_configured,
    proofFile: response.proof_file,
  };
}

function mapQwenCloudShowcase(response: ApiQwenCloudShowcaseResponse): QwenCloudShowcase {
  return {
    generatedAt: response.generated_at,
    projectTitle: response.project_title,
    track: response.track,
    elevatorPitch: response.elevator_pitch,
    runtime: {
      status: response.runtime.status,
      service: response.runtime.service,
      track: response.runtime.track,
      deploymentTarget: response.runtime.deployment_target,
      alibabaCloudRegion: response.runtime.alibaba_cloud_region ?? null,
      alibabaCloudService: response.runtime.alibaba_cloud_service ?? null,
      llmProvider: response.runtime.llm_provider,
      llmModel: response.runtime.llm_model ?? null,
      llmApiKeyConfigured: response.runtime.llm_api_key_configured,
      proofFile: response.runtime.proof_file,
      qwenCloudReady: response.runtime.qwen_cloud_ready,
      alibabaRuntimeReady: response.runtime.alibaba_runtime_ready,
      liveBackendReady: response.runtime.live_backend_ready,
    },
    judgeFlow: response.judge_flow.map((step) => ({
      order: step.order,
      title: step.title,
      route: step.route,
      outcome: step.outcome,
      evidencePaths: step.evidence_paths,
    })),
    evidence: response.evidence.map((item) => ({
      name: item.name,
      state: item.state,
      proofPaths: item.proof_paths,
    })),
    benchmark: {
      status: response.benchmark.status,
      runId: response.benchmark.run_id ?? null,
      provider: response.benchmark.provider ?? null,
      model: response.benchmark.model ?? null,
      caseCount: response.benchmark.case_count,
      baselineScore: response.benchmark.baseline_score,
      dreamScore: response.benchmark.dream_score,
      scoreDelta: response.benchmark.score_delta,
      medianDelta: response.benchmark.median_delta,
      exactPairedPermutationP: response.benchmark.exact_paired_permutation_p ?? null,
      dreamWins: response.benchmark.dream_wins,
      exactRetrievalRecallAt12: response.benchmark.exact_retrieval_recall_at_12,
      reportPath: response.benchmark.report_path ?? null,
      limitations: response.benchmark.limitations,
    },
    experienceBenchmark: {
      status: response.experience_benchmark.status,
      runId: response.experience_benchmark.run_id ?? null,
      provider: response.experience_benchmark.provider ?? null,
      model: response.experience_benchmark.model ?? null,
      caseCount: response.experience_benchmark.case_count,
      curatorDecisionCount: response.experience_benchmark.decision_count,
      lifecycleCasesPassed: response.experience_benchmark.passed_cases,
      lifecycleCasePassRate:
        response.experience_benchmark.case_count > 0
          ? response.experience_benchmark.passed_cases / response.experience_benchmark.case_count
          : 0,
      proposalAccuracy: response.experience_benchmark.proposal_accuracy,
      governedActionAccuracy: response.experience_benchmark.action_accuracy,
      criticalMemoryRecall: response.experience_benchmark.critical_memory_recall,
      forbiddenMemoryLeakRate: response.experience_benchmark.forbidden_memory_leak_rate,
      tokenBudgetCompliance: response.experience_benchmark.token_budget_compliance,
      overallScore: response.experience_benchmark.overall_score,
      reportPath: response.experience_benchmark.report_path ?? null,
      limitations: response.experience_benchmark.limitations,
    },
    scorecard: {
      weightedCurrentEvidenceReady: response.scorecard.weighted_current_evidence_ready,
      weightedStaticEvidenceReady: response.scorecard.weighted_static_evidence_ready,
      weightedTotal: response.scorecard.weighted_total,
      liveBackendPoints: response.scorecard.live_backend_points,
      publicVideoPoints: response.scorecard.public_video_points,
      missingExternalInputs: response.scorecard.missing_external_inputs,
    },
  };
}

function mapExperienceMemory(memory: ApiExperienceMemory): ExperienceMemory {
  return {
    memoryId: memory.memory_id,
    teamId: memory.team_id,
    userId: memory.user_id,
    kind: memory.kind,
    key: memory.key,
    value: memory.value,
    status: memory.status,
    confidence: memory.confidence,
    importance: memory.importance,
    sourceSessionId: memory.source_session_id,
    sourceReference: memory.source_reference,
    createdAt: memory.created_at,
    updatedAt: memory.updated_at,
    validFrom: memory.valid_from,
    validUntil: memory.valid_until ?? null,
    supersededBy: memory.superseded_by ?? null,
    lastRecalledAt: memory.last_recalled_at ?? null,
    recallCount: memory.recall_count,
    feedbackCount: memory.feedback_count,
    helpfulTotal: memory.helpful_total,
    correctnessTotal: memory.correctness_total,
  };
}

function mapExperienceDecision(decision: ApiExperienceDecision): ExperienceDecision {
  return {
    decisionId: decision.decision_id,
    teamId: decision.team_id,
    userId: decision.user_id,
    sessionId: decision.session_id,
    requestedAction: decision.requested_action,
    action: decision.action,
    targetMemoryId: decision.target_memory_id ?? null,
    createdMemoryId: decision.created_memory_id ?? null,
    rationale: decision.rationale,
    providerName: decision.provider_name,
    modelName: decision.model_name,
    tokenUsage: decision.token_usage ?? null,
    createdAt: decision.created_at,
  };
}

function mapExperienceCaptureResult(
  result: ApiExperienceCaptureResult,
): ExperienceCaptureResult {
  return {
    decision: mapExperienceDecision(result.decision),
    memory: result.memory ? mapExperienceMemory(result.memory) : null,
    affectedMemories: result.affected_memories.map(mapExperienceMemory),
    activeMemoryCount: result.active_memory_count,
  };
}

function mapExperienceRecallResult(result: ApiExperienceRecallResult): ExperienceRecallResult {
  const mapCandidate = (candidate: ApiExperienceRecallCandidate): ExperienceRecallCandidate => ({
    memory: mapExperienceMemory(candidate.memory),
    score: candidate.score,
    estimatedTokens: candidate.estimated_tokens,
    selected: candidate.selected,
    reason: candidate.reason,
  });
  return {
    teamId: result.team_id,
    userId: result.user_id,
    sessionId: result.session_id,
    query: result.query,
    tokenBudget: result.token_budget,
    estimatedTokensUsed: result.estimated_tokens_used,
    selected: result.selected.map(mapCandidate),
    excluded: result.excluded.map(mapCandidate),
    expiredMemoryIds: result.expired_memory_ids,
    contextCard: result.context_card,
  };
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
    waivedReason: question.waived_reason ?? undefined,
    waivedBy: question.waived_by ?? undefined,
    waivedAt: question.waived_at ?? undefined,
  };
}

function mapContextRetrievalStep(step: ApiContextRetrievalStep): ContextRetrievalStep {
  return {
    stepName: step.step_name,
    query: step.query,
    provider: step.provider,
    candidatesFound: step.candidates_found,
    selectedCount: step.selected_count,
    notes: step.notes,
  };
}

function mapContextEvidenceCandidate(candidate: ApiEvidenceCandidate): ContextEvidenceCandidate {
  return {
    evidenceId: candidate.evidence_id,
    sourceType: candidate.source_type,
    title: candidate.title,
    sourcePath: candidate.source_path,
    excerpt: candidate.excerpt,
    score: Number(candidate.score.toFixed(2)),
    reason: candidate.reason,
    selected: candidate.selected,
    excludedReason: candidate.excluded_reason,
    concepts: candidate.concepts,
    authorityStatus: candidate.authority_status,
  };
}

function mapContextMemoryIntakeSectionProof(
  proof: ApiMemoryIntakeSectionProof,
): ContextMemoryIntakeSectionProof {
  return {
    sectionId: proof.section_id,
    heading: proof.heading,
    sourceReference: proof.source_reference,
    startLine: proof.start_line,
    endLine: proof.end_line,
    sectionHash: proof.section_hash,
  };
}

function mapContextMemoryIntakeProof(proof: ApiMemoryIntakeProof): ContextMemoryIntakeProof {
  return {
    documentId: proof.document_id,
    draftId: proof.draft_id,
    originalPath: proof.original_path,
    storedPath: proof.stored_path,
    promotedPath: proof.promoted_path,
    sourceHash: proof.source_hash,
    sourceHashVerified: proof.source_hash_verified,
    reviewStatus: proof.review_status,
    matchExplanation: proof.match_explanation,
    matchedTerms: proof.matched_terms ?? [],
    intakeAuditRunIds: proof.intake_audit_run_ids,
    sectionProofs: proof.section_proofs.map(mapContextMemoryIntakeSectionProof),
  };
}

function mapMemoryReviewEvent(event: ApiMemoryReviewEvent): MemoryReviewEvent {
  return {
    eventId: event.event_id,
    teamId: event.team_id,
    claimId: event.claim_id,
    scanId: event.scan_id,
    previousStatus: event.previous_status,
    newStatus: event.new_status,
    reviewer: event.reviewer,
    reason: event.reason,
    reviewedAt: event.reviewed_at,
    reviewerSignature: event.reviewer_signature,
    fieldDiffs: (event.field_diffs ?? []).map((diff) => ({
      fieldPath: diff.field_path,
      before: diff.before,
      after: diff.after,
    })),
    claimSnapshot: event.claim_snapshot
      ? {
          claimId: event.claim_snapshot.claim_id,
          entityType: event.claim_snapshot.entity_type,
          entityName: event.claim_snapshot.entity_name,
          relationType: event.claim_snapshot.relation_type,
          relationValue: event.claim_snapshot.relation_value,
          extractionMethod: event.claim_snapshot.extraction_method,
          confidence: Number(event.claim_snapshot.confidence.toFixed(2)),
          riskLevel: event.claim_snapshot.risk_level,
          securityClassification: event.claim_snapshot.security_classification,
          evidencePaths: event.claim_snapshot.evidence_paths,
          intakeDocumentIds: event.claim_snapshot.intake_document_ids,
          sourceHashes: event.claim_snapshot.source_hashes,
        }
      : null,
    riskSignals: event.risk_signals ?? [],
    conflictSignals: event.conflict_signals ?? [],
    signalExplanations: (event.signal_explanations ?? []).map((item) => ({
      signal: item.signal,
      category: item.category,
      severity: item.severity,
      explanation: item.explanation,
      evidence: item.evidence ?? [],
    })),
  };
}

function mapMemoryLedgerSnapshot(ledger: ApiMemoryLedgerSnapshot): MemoryLedgerSnapshot {
  return {
    teamId: ledger.team_id,
    updatedAt: ledger.updated_at,
    events: ledger.events.map(mapMemoryReviewEvent),
  };
}

function mapMemoryConflictClaimSide(
  side: ApiMemoryConflictClaimSide,
): MemoryConflictClaimSide {
  return {
    claim: mapMemoryClaim(side.claim),
    effectiveStatus: side.effective_status,
    relationValue: side.relation_value,
    evidencePaths: side.evidence_paths ?? [],
    intakeDocumentIds: side.intake_document_ids ?? [],
    latestReview: side.latest_review ? mapMemoryReviewEvent(side.latest_review) : null,
  };
}

function mapMemoryConflictPair(pair: ApiMemoryConflictPair): MemoryConflictPair {
  return {
    conflictId: pair.conflict_id,
    teamId: pair.team_id,
    scanId: pair.scan_id,
    entityId: pair.entity_id,
    entityName: pair.entity_name,
    entityType: pair.entity_type,
    relationType: pair.relation_type,
    left: mapMemoryConflictClaimSide(pair.left),
    right: mapMemoryConflictClaimSide(pair.right),
    signal: {
      signal: pair.signal.signal,
      category: pair.signal.category,
      severity: pair.signal.severity,
      explanation: pair.signal.explanation,
      evidence: pair.signal.evidence ?? [],
    },
  };
}

function mapMemoryConflictReport(report: ApiMemoryConflictReport): MemoryConflictReport {
  return {
    teamId: report.team_id,
    scanId: report.scan_id,
    generatedAt: report.generated_at,
    conflictCount: report.conflict_count,
    pairs: report.pairs.map(mapMemoryConflictPair),
  };
}

function mapMemoryConflictResolutionEvent(
  event: ApiMemoryConflictResolutionEvent,
): MemoryConflictResolutionEvent {
  return {
    eventId: event.event_id,
    teamId: event.team_id,
    scanId: event.scan_id,
    conflictId: event.conflict_id,
    action: event.action,
    winningClaimId: event.winning_claim_id,
    rejectedClaimId: event.rejected_claim_id,
    reviewer: event.reviewer,
    reason: event.reason,
    resolvedAt: event.resolved_at,
    reviewerSignature: event.reviewer_signature,
    reviewEventIds: event.review_event_ids,
    conflictSnapshot: mapMemoryConflictPair(event.conflict_snapshot),
  };
}

function mapMemoryConflictResolutionLedger(
  ledger: ApiMemoryConflictResolutionLedger,
): MemoryConflictResolutionLedger {
  return {
    teamId: ledger.team_id,
    updatedAt: ledger.updated_at,
    events: ledger.events.map(mapMemoryConflictResolutionEvent),
  };
}

function mapMemoryClaim(claim: ApiMemoryClaim): MemoryClaim {
  return {
    claimId: claim.claim_id,
    teamId: claim.team_id,
    repoId: claim.repo_id,
    scanId: claim.scan_id,
    entity: {
      entityId: claim.entity.entity_id,
      entityType: claim.entity.entity_type,
      canonicalName: claim.entity.canonical_name,
      aliases: claim.entity.aliases,
    },
    relation: {
      type: claim.relation.type,
      objectEntityId: claim.relation.object_entity_id,
      value: claim.relation.value,
      condition: claim.relation.condition,
    },
    evidence: {
      sourceIds: claim.evidence.source_ids,
      spans: claim.evidence.spans.map((span) => ({
        sourceId: span.source_id,
        sourceType: span.source_type,
        path: span.path,
        commitSha: span.commit_sha,
        startLine: span.start_line,
        endLine: span.end_line,
        excerptHash: span.excerpt_hash,
        spanId: span.span_id,
      })),
      intakeProofs: (claim.evidence.intake_proofs ?? []).map(mapContextMemoryIntakeProof),
    },
    extractionMethod: claim.extraction.method,
    extractorVersion: claim.extraction.extractor_version,
    confidence: Number(claim.extraction.confidence.toFixed(2)),
    governanceStatus: claim.governance.status,
    riskLevel: claim.governance.risk_level,
    createdAt: claim.audit.created_at,
    updatedAt: claim.audit.updated_at,
  };
}

function mapMemoryDiffResult(diff: ApiMemoryDiffResult): MemoryDiffResult {
  return {
    teamId: diff.team_id,
    scanId: diff.scan_id,
    baseScanId: diff.base_scan_id,
    addedClaims: diff.added_claims.map(mapMemoryClaim),
    removedClaims: diff.removed_claims.map(mapMemoryClaim),
    changedClaims: diff.changed_claims.map(mapMemoryClaim),
    unchangedCount: diff.unchanged_count,
    markdown: diff.markdown,
  };
}

function mapMemoryScanResult(scan: ApiMemoryScanResult): MemoryScanResult {
  return {
    scanId: scan.scan_id,
    teamId: scan.team_id,
    repoName: scan.repo_name,
    createdAt: scan.created_at,
    claims: scan.claims.map(mapMemoryClaim),
    summary: scan.summary,
    warnings: scan.warnings,
  };
}

function mapContextMemoryClaim(
  claim: ApiMemoryClaimReference,
): ContextMemoryClaimReference {
  return {
    claimId: claim.claim_id,
    status: claim.status,
    entity: claim.entity,
    relation: claim.relation,
    value: claim.value,
    evidencePaths: claim.evidence_paths,
    intakeProofs: (claim.intake_proofs ?? []).map(mapContextMemoryIntakeProof),
    reason: claim.reason,
  };
}

function mapContextGraphPath(path: ApiGraphPathReference): ContextGraphPathReference {
  return {
    query: path.query,
    path: path.path,
    sourcePaths: path.source_paths,
  };
}

function mapContextRetrievalTrail(trail: ApiContextRetrievalTrail): ContextRetrievalTrail {
  return {
    trailId: trail.trail_id,
    runId: trail.run_id,
    caseId: trail.case_id,
    reviewId: trail.review_id,
    teamId: trail.team_id,
    repoName: trail.repo_name,
    rawQuery: trail.raw_query,
    detectedConcepts: trail.detected_concepts,
    retrievalSteps: trail.retrieval_steps.map(mapContextRetrievalStep),
    candidateEvidence: trail.candidate_evidence.map(mapContextEvidenceCandidate),
    selectedEvidence: trail.selected_evidence.map(mapContextEvidenceCandidate),
    excludedEvidence: trail.excluded_evidence.map(mapContextEvidenceCandidate),
    rankingReasons: trail.ranking_reasons,
    graphExpansionPaths: trail.graph_expansion_paths.map(mapContextGraphPath),
    memoryClaimsConsidered: trail.memory_claims_considered.map(mapContextMemoryClaim),
    memoryClaimsUsed: trail.memory_claims_used.map(mapContextMemoryClaim),
    warnings: trail.warnings,
    finalContextSummary: trail.final_context_summary,
    jsonPath: trail.json_path,
    markdownPath: trail.markdown_path,
  };
}

function mapContextPack(pack: ApiContextPack): ContextPack {
  return {
    contextPackId: pack.context_pack_id,
    caseId: pack.case_id,
    runId: pack.run_id,
    reviewId: pack.review_id,
    teamId: pack.team_id,
    repoName: pack.repo_name,
    userRequest: pack.user_request,
    selectedDocs: pack.selected_docs.map(mapContextEvidenceCandidate),
    selectedCode: pack.selected_code.map(mapContextEvidenceCandidate),
    selectedTests: pack.selected_tests.map(mapContextEvidenceCandidate),
    selectedIncidents: pack.selected_incidents.map(mapContextEvidenceCandidate),
    selectedHistoricalJira: pack.selected_historical_jira.map(mapContextEvidenceCandidate),
    selectedHistoricalPr: pack.selected_historical_pr.map(mapContextEvidenceCandidate),
    selectedMemoryClaims: pack.selected_memory_claims.map(mapContextMemoryClaim),
    candidateMemoryClaims: pack.candidate_memory_claims.map(mapContextMemoryClaim),
    excludedEvidence: pack.excluded_evidence.map(mapContextEvidenceCandidate),
    graphPaths: pack.graph_paths.map(mapContextGraphPath),
    deterministicSizeBudget: pack.deterministic_size_budget,
    selectedEvidenceCount: pack.selected_evidence_count,
    warnings: pack.warnings,
    jsonPath: pack.json_path,
    markdownPath: pack.markdown_path,
  };
}

function mapContextPromptPreview(preview: ApiContextPromptPreview): ContextPromptPreview {
  return {
    previewId: preview.preview_id,
    caseId: preview.case_id,
    runId: preview.run_id,
    target: preview.target,
    providerMode: preview.provider_mode,
    promptText: preview.prompt_text,
    evidencePaths: preview.evidence_paths,
    warnings: preview.warnings,
    jsonPath: preview.json_path,
    markdownPath: preview.markdown_path,
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
    llmJudge: scorecard.llm_judge ? mapLLMJudge(scorecard.llm_judge) : undefined,
  };
}

function mapLLMJudge(judge: ApiLLMJudgeResult): LLMJudgeResult {
  return {
    status: judge.status === 'completed' ? 'completed' : 'failed',
    provider: judge.provider ?? undefined,
    model: judge.model ?? undefined,
    promptVersion: judge.prompt_version,
    inputHash: judge.input_hash ?? undefined,
    durationMs: judge.duration_ms ?? undefined,
    readiness: judge.readiness ?? undefined,
    confidence: judge.confidence ?? undefined,
    summary: judge.summary ?? undefined,
    risks: judge.risks,
    missingEvidence: judge.missing_evidence,
    recommendations: judge.recommendations,
    warning: judge.warning ?? undefined,
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

function mapHumanRating(rating: ApiHumanRating): HumanRating {
  return {
    runId: rating.run_id,
    usefulnessScore: rating.usefulness_score,
    correctnessScore: rating.correctness_score,
    comments: rating.comments,
    createdAt: rating.created_at,
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
    sourceHash: document.source_hash,
    promotedPath: document.promoted_path,
    status: document.status,
    createdAt: document.created_at,
    updatedAt: document.updated_at,
    warnings: document.warnings,
  };
}

function mapKnowledgeDraft(draft: ApiKnowledgeDraft): KnowledgeDraft {
  return {
    draftId: draft.draft_id,
    documentId: draft.document_id,
    teamId: draft.team_id,
    title: draft.title,
    targetDocType: draft.target_doc_type,
    sourceHash: draft.source_hash,
    app: draft.app,
    component: draft.component,
    sections: draft.sections.map((section) => ({
      sectionId: section.section_id,
      heading: section.heading,
      level: section.level,
      text: section.text,
      concepts: section.concepts,
      sourceReference: section.source_reference,
      sourceSpan: section.source_span
        ? {
            startLine: section.source_span.start_line,
            endLine: section.source_span.end_line,
          }
        : null,
      sectionHash: section.section_hash,
    })),
    concepts: draft.concepts.map((concept) => ({
      concept: concept.concept,
      sourceSections: concept.source_sections,
      confidence: concept.confidence,
    })),
    reviewStatus: draft.review_status,
    reviewer: draft.reviewer,
    reviewNotes: draft.review_notes,
    promotedPath: draft.promoted_path,
    warnings: draft.warnings,
    jsonPath: draft.json_path,
    markdownPath: draft.markdown_path,
    normalizedMarkdown: draft.normalized_markdown,
  };
}

function mapIntakeDocumentDetail(detail: ApiIntakeDocumentDetail): IntakeDocumentDetail {
  const document = mapIntakeDocument(detail.document);
  return {
    document,
    draft: detail.draft ? mapKnowledgeDraft(detail.draft) : null,
    rawText: detail.raw_text,
    rawTextTruncated: detail.raw_text_truncated,
    rawSizeBytes: detail.raw_size_bytes,
    rawTextAvailable: detail.raw_text_available,
    rawTextWarning: detail.raw_text_warning,
    sourceHashVerified: detail.source_hash_verified,
    auditEvents: detail.audit_events.map((record) => mapAuditRun(record, document.title)),
    reviewEvents: (detail.review_events ?? []).map(mapDraftReviewEvent),
    downstreamEvents: detail.downstream_events.map((record) =>
      mapAuditRun(record, document.title),
    ),
    downstreamUsages: detail.downstream_usages.map((usage) =>
      mapDownstreamUsage(usage, document.title),
    ),
  };
}

function mapDraftReviewEvent(event: ApiDraftReviewEvent): DraftReviewEvent {
  return {
    eventId: event.event_id,
    eventType: event.event_type,
    draftId: event.draft_id,
    documentId: event.document_id,
    teamId: event.team_id,
    createdAt: event.created_at,
    reviewer: event.reviewer,
    notes: event.notes,
    previousStatus: event.previous_status,
    newStatus: event.new_status,
    auditRunId: event.audit_run_id,
    metadataSnapshot: {
      title: event.metadata_snapshot.title,
      targetDocType: event.metadata_snapshot.target_doc_type,
      app: event.metadata_snapshot.app,
      component: event.metadata_snapshot.component,
      concepts: event.metadata_snapshot.concepts,
      reviewStatus: event.metadata_snapshot.review_status,
      promotedPath: event.metadata_snapshot.promoted_path,
    },
    metadataDiff: event.metadata_diff.map((diff) => ({
      field: diff.field,
      before: diff.before,
      after: diff.after,
    })),
    sourceHash: event.source_hash,
    sectionHashes: event.section_hashes,
    warnings: event.warnings,
  };
}

function mapDownstreamUsage(usage: ApiDownstreamUsage, defaultApp: string): DownstreamUsage {
  return {
    auditRun: mapAuditRun(usage.audit_record, defaultApp),
    matchedSourcePaths: usage.matched_source_paths,
    matchReason: usage.match_reason,
    detailRoute: usage.detail_route,
    matchProofs: (usage.match_proofs ?? []).map(mapSourceMatchProof),
  };
}

function mapSectionMatchProof(proof: ApiSectionMatchProof): SectionMatchProof {
  return {
    sectionId: proof.section_id,
    heading: proof.heading,
    sourceReference: proof.source_reference,
    sourceSpan: proof.source_span
      ? {
          startLine: proof.source_span.start_line,
          endLine: proof.source_span.end_line,
        }
      : null,
    sectionHash: proof.section_hash,
  };
}

function mapSourceMatchProof(proof: ApiSourceMatchProof): SourceMatchProof {
  return {
    retrievedSourcePath: proof.retrieved_source_path,
    matchedPath: proof.matched_path,
    matchedLabel: proof.matched_label,
    documentId: proof.document_id,
    draftId: proof.draft_id,
    sourceHash: proof.source_hash,
    sourceHashVerified: proof.source_hash_verified,
    sectionProofs: proof.section_proofs.map(mapSectionMatchProof),
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
    modelProvider: 'qwen-cloud',
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
    'requirement_question_waive',
    'engineering_brief',
    'jira_draft_context',
    'jira_draft',
    'jira_readiness_check',
    'pr_review_summary',
    'knowledge_search',
    'knowledge_intake',
    'knowledge_intake_upload',
    'knowledge_intake_parse',
    'knowledge_intake_metadata_update',
    'knowledge_intake_review',
    'knowledge_intake_promote',
    'context_intelligence',
    'retrieval_context_eval',
    'codebase_index',
    'evidence_graph',
    'testgen_stub',
    'audit_eval',
    'evaluation_scorecard',
    'eval_scorecard',
    'llm_judge_eval',
  ];
  return allowed.includes(value as WorkflowType) ? (value as WorkflowType) : 'audit_eval';
}

function runStatusFromValue(value: string): RunStatus {
  const allowed: RunStatus[] = [
    'success',
    'completed',
    'created',
    'answered',
    'waived',
    'uploaded',
    'parsed',
    'approved',
    'promoted',
    'needs_review',
    'pending_review',
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
