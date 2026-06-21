package com.democorp.dfp.execution;

/** Synthetic DFP code for DREAM codebase memory demos. */
import java.util.ArrayList; import java.util.List; public class Execution { public String executionId; public String jobId; public ExecutionStatus status = ExecutionStatus.QUEUED; public String startTime; public String endTime; public List<TaskExecution> taskExecutions = new ArrayList<>(); }
