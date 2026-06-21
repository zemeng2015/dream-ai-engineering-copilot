package com.democorp.dfp.workflow;

/** Synthetic DFP code for DREAM codebase memory demos. */
import java.util.List; public class WorkflowDefinition { public String workflowId; public String version; public boolean published; public List<TaskDefinition> tasks; public boolean isImmutableForJobs() { return published; } }
