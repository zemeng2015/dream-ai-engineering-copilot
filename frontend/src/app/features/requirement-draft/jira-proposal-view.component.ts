// SPDX-License-Identifier: Apache-2.0

import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Params, RouterLink } from '@angular/router';

import type { ClarificationQuestion } from '../../core/dream-models';

interface JiraProposalSection {
  heading: string;
  body: string;
}

interface JiraProposalView {
  title: string;
  intro: string;
  sections: JiraProposalSection[];
}

export interface JiraProposalReferenceLink {
  label: string;
  detail: string;
  kind: string;
  route?: string[] | null;
  queryParams?: Params | null;
}

interface JiraProposalBodyBlock {
  kind: 'text' | 'references';
  text?: string;
  references?: JiraProposalReferenceLink[];
}

interface QuestionWaiverDraft {
  reason: string;
  note: string;
}

@Component({
  selector: 'app-jira-proposal-view',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './jira-proposal-view.component.html',
  styleUrl: './jira-proposal-view.component.scss',
})
export class JiraProposalViewComponent {
  view: JiraProposalView = parseJiraProposal('');
  @Input() questions: ClarificationQuestion[] = [];
  @Input() questionAnswers: Record<string, string> = {};
  @Input() questionWaivers: Record<string, QuestionWaiverDraft> = {};
  @Input() waiverReasons: string[] = [];
  @Input() savingQuestionId: string | null = null;
  @Input() sourceLinks: JiraProposalReferenceLink[] = [];
  @Input() affectedFileLinks: JiraProposalReferenceLink[] = [];
  @Output() readonly questionAnswerChange = new EventEmitter<{ questionId: string; value: string }>();
  @Output() readonly questionAnswerSave = new EventEmitter<string>();
  @Output() readonly questionWaiverReasonChange = new EventEmitter<{ questionId: string; value: string }>();
  @Output() readonly questionWaiverNoteChange = new EventEmitter<{ questionId: string; value: string }>();
  @Output() readonly questionWaive = new EventEmitter<string>();

  @Input() set markdown(value: string) {
    this.view = parseJiraProposal(value);
  }

  isOpenQuestionsSection(section: JiraProposalSection): boolean {
    return normalizeHeading(section.heading) === 'open questions';
  }

  isSourcesSection(section: JiraProposalSection): boolean {
    return normalizeHeading(section.heading) === 'sources used';
  }

  bodyBlocks(section: JiraProposalSection): JiraProposalBodyBlock[] {
    const lines = section.body.split(/\r?\n/);
    const blocks: JiraProposalBodyBlock[] = [];

    for (const line of lines) {
      const text = cleanListText(line);
      if (!text) {
        continue;
      }
      const references = this.referencesFromLine(text);
      if (references.length) {
        const previous = blocks[blocks.length - 1];
        if (previous?.kind === 'references') {
          previous.references = [...(previous.references ?? []), ...references];
        } else {
          blocks.push({ kind: 'references', references });
        }
        continue;
      }
      blocks.push({ kind: 'text', text: stripInlineMarkdown(text) });
    }

    return blocks;
  }

  sectionReferences(section: JiraProposalSection): JiraProposalReferenceLink[] {
    if (this.isSourcesSection(section) && this.sourceLinks.length) {
      return this.sourceLinks;
    }
    return this.bodyBlocks(section).flatMap((block) => block.references ?? []);
  }

  answerValue(question: ClarificationQuestion): string {
    return this.questionAnswers[question.questionId] || question.answer || '';
  }

  waiverValue(question: ClarificationQuestion): QuestionWaiverDraft {
    return (
      this.questionWaivers[question.questionId] ?? {
        reason: this.waiverReasons[0] ?? 'Out of scope for this release',
        note: '',
      }
    );
  }

  waiverSummary(question: ClarificationQuestion): string {
    return question.waivedReason || question.answer || 'Question waived for this Jira handoff.';
  }

  isSaving(question: ClarificationQuestion): boolean {
    return this.savingQuestionId === question.questionId;
  }

  onAnswerInput(questionId: string, event: Event): void {
    const value = event.target instanceof HTMLTextAreaElement ? event.target.value : '';
    this.questionAnswerChange.emit({ questionId, value });
  }

  onWaiverReasonInput(questionId: string, event: Event): void {
    const value = event.target instanceof HTMLSelectElement ? event.target.value : '';
    this.questionWaiverReasonChange.emit({ questionId, value });
  }

  onWaiverNoteInput(questionId: string, event: Event): void {
    const value = event.target instanceof HTMLInputElement ? event.target.value : '';
    this.questionWaiverNoteChange.emit({ questionId, value });
  }

  private referencesFromLine(text: string): JiraProposalReferenceLink[] {
    const markdownLinks = [...text.matchAll(/\[([^\]]+)\]\(([^)]+)\)/g)];
    if (markdownLinks.length) {
      return markdownLinks.map((match) => this.decorateReference(match[2], match[1], typeHintFromLine(text)));
    }

    const codeRefs = [...text.matchAll(/`([^`]+)`/g)].map((match) => match[1]);
    if (codeRefs.length) {
      return codeRefs.map((raw) => this.decorateReference(raw, undefined, typeHintFromLine(text)));
    }

    if (looksLikeReference(text)) {
      return [this.decorateReference(text, undefined, typeHintFromLine(text))];
    }

    return [];
  }

  private decorateReference(raw: string, labelHint?: string, kindHint?: string): JiraProposalReferenceLink {
    const normalized = normalizeReference(raw);
    const known =
      this.affectedFileLinks.find((reference) => referenceMatches(reference.detail, normalized)) ??
      this.sourceLinks.find((reference) => referenceMatches(reference.detail, normalized));
    return {
      label: known?.label ?? referenceLabel(normalized, labelHint),
      detail: known?.detail ?? normalized,
      kind: known?.kind ?? referenceKind(normalized, kindHint),
      route: known?.route ?? fallbackRoute(normalized),
      queryParams: known?.queryParams ?? fallbackQueryParams(normalized),
    };
  }
}

function parseJiraProposal(markdown: string): JiraProposalView {
  const lines = markdown.split(/\r?\n/);
  let title = 'Jira Story Draft';
  const intro: string[] = [];
  const sections: JiraProposalSection[] = [];
  let current: JiraProposalSection | null = null;

  for (const line of lines) {
    if (line.startsWith('# ')) {
      title = line.replace(/^#\s+/, '').trim() || title;
      continue;
    }
    if (line.startsWith('## ')) {
      if (current) {
        current.body = current.body.trim();
        sections.push(current);
      }
      current = { heading: line.replace(/^##\s+/, '').trim(), body: '' };
      continue;
    }
    if (current) {
      current.body += `${line}\n`;
    } else if (line.trim()) {
      intro.push(line.trim());
    }
  }
  if (current) {
    current.body = current.body.trim();
    sections.push(current);
  }

  return {
    title,
    intro: intro.join(' '),
    sections,
  };
}

function normalizeHeading(value: string): string {
  return value.trim().toLowerCase();
}

function cleanListText(value: string): string {
  return value.trim().replace(/^[-*]\s+/, '').trim();
}

function stripInlineMarkdown(value: string): string {
  return value.replace(/`([^`]+)`/g, '$1').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
}

function normalizeReference(value: string): string {
  return value
    .replace(/^[-*]\s+/, '')
    .replace(/^`|`$/g, '')
    .replace(/[.,;:]$/g, '')
    .trim();
}

function referenceLabel(raw: string, labelHint?: string): string {
  const conceptIndex = raw.indexOf('#concept:');
  if (conceptIndex >= 0) {
    return raw.slice(conceptIndex + '#concept:'.length).trim() || 'concept';
  }
  const path = raw.split('#')[0];
  const fileName = path.split('/').filter(Boolean).pop();
  if (fileName) {
    return fileName;
  }
  return labelHint?.trim() || raw;
}

function referenceKind(raw: string, kindHint?: string): string {
  const hint = kindHint?.replace(/:$/, '').trim();
  if (raw.includes('#concept:')) {
    return raw.startsWith('evidence-graph') ? 'Graph evidence' : 'Concept';
  }
  if (hint && /incident|jira|pull request/i.test(hint)) {
    return hint;
  }
  if (/\.(java|ts|tsx|js|jsx|py|go|rb|cs|kt|scala)$/i.test(raw)) {
    return /test|spec/i.test(raw) ? 'Test file' : 'Code file';
  }
  if (/\.md$/i.test(raw)) {
    return 'Doc';
  }
  return hint || 'Source';
}

function typeHintFromLine(text: string): string | undefined {
  const match = text.match(/^([^:[\]`]+):\s+/);
  return match?.[1]?.trim();
}

function looksLikeReference(text: string): boolean {
  return (
    text.includes('#concept:') ||
    /(?:^|\/)[^/\s]+\.(java|ts|tsx|js|jsx|py|go|rb|cs|kt|scala|md)$/i.test(text)
  );
}

function referenceMatches(candidate: string, raw: string): boolean {
  const left = normalizeComparable(candidate);
  const right = normalizeComparable(raw);
  return left === right || left.endsWith(`/${right}`) || right.endsWith(`/${left}`);
}

function normalizeComparable(value: string): string {
  return value.replace(/\\/g, '/').trim().toLowerCase();
}

function fallbackRoute(raw: string): string[] | null {
  return /\.(java|ts|tsx|js|jsx|py|go|rb|cs|kt|scala)$/i.test(raw) ? ['/codebase'] : null;
}

function fallbackQueryParams(raw: string): Params | null {
  return fallbackRoute(raw) ? { file: raw } : null;
}
