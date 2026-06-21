package com.democorp.dfp.execution;

/** Synthetic DFP code for DREAM codebase memory demos. */
public class ExecutionController { private final ExecutionService executionService = new ExecutionService(); public Execution startExecution(String jobId) { return executionService.startExecution(jobId, TaskType.BATCH_TASK); } public String status(String executionId) { return "status:" + executionId; } }
