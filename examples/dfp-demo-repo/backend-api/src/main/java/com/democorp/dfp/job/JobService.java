package com.democorp.dfp.job;

/** Synthetic DFP code for DREAM codebase memory demos. */
public class JobService { public Job createJob(String name, String owner, String workflowId, String workflowVersion) { Job job = new Job(); job.id = "job-demo-" + Math.abs(name.hashCode()); job.name = name; job.owner = owner; job.workflowId = workflowId; job.workflowVersion = workflowVersion; job.status = "DRAFT"; return job; } public boolean canExecute(Job job) { return job != null && !"RUNNING".equals(job.status); } }
