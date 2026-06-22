// SPDX-License-Identifier: Apache-2.0

export class JobDetailComponent { selectedWorkflowVersion = 'baseline-v3'; validateTaskUpload(taskId: string, fileName: string): string { return taskId && fileName ? 'valid' : 'missing task upload'; } executeJob(): string { return 'Execution queued'; } }
