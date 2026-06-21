package com.democorp.dfp.adapters;

/** Synthetic DFP code for DREAM codebase memory demos. */
public class BatchJobAdapter { public String submitBatchTask(String executionId, String taskId) { return "batch-" + executionId + "-" + taskId; } public boolean isRetryAllowed(String taskId, int attemptCount) { return taskId != null && attemptCount < 3; } }
