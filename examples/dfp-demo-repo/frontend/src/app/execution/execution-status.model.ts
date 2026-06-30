// SPDX-License-Identifier: Apache-2.0

export type ExecutionStatus = 'QUEUED' | 'RUNNING' | 'FAILED' | 'COMPLETED' | 'CANCELLED' | 'PARTIAL_SUCCESS'; export type TaskStatus = 'PENDING' | 'QUEUED' | 'RUNNING' | 'FAILED' | 'COMPLETED' | 'SKIPPED' | 'RETRYING'; export interface ExecutionStatusView { executionId: string; status: ExecutionStatus; activeTaskId?: string; staleRunning: boolean; }
