package com.democorp.dfp.workflow;

/** Synthetic DFP code for DREAM codebase memory demos. */
import java.util.List; public class TaskDefinition { public String taskId; public String displayName; public TaskType taskType; public List<String> dependencies; public int timeoutSeconds; public int maxRetryAttempts; public List<String> requiredConfigFields; public boolean requiresConfigField(String fieldName) { return requiredConfigFields != null && requiredConfigFields.contains(fieldName); } }
