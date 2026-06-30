// SPDX-License-Identifier: Apache-2.0

package com.democorp.dfp.job;

/** Synthetic DFP code for DREAM codebase memory demos. */
public class JobController { private final JobService jobService = new JobService(); public Job createJob(String name, String owner, String workflowId, String workflowVersion) { return jobService.createJob(name, owner, workflowId, workflowVersion); } public String validateTaskConfigBeforeExecution(String taskId, String configJson) { if (configJson == null || !configJson.contains("forecastHorizon")) { return "Missing required task config field forecastHorizon"; } return "valid"; } }
