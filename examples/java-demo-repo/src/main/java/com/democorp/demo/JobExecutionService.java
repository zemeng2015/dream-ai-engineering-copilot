// SPDX-License-Identifier: Apache-2.0

package com.democorp.demo;

/**
 * Coordinates the fake long-running job execution workflow for DemoCorp demos.
 */
public class JobExecutionService {
    private final AsyncJobStatusTracker statusTracker;
    private final BatchJobAdapter batchJobAdapter;
    private final JobResultCollector resultCollector;

    public JobExecutionService() {
        this(new AsyncJobStatusTracker(), new BatchJobAdapter(), new JobResultCollector());
    }

    public JobExecutionService(
            AsyncJobStatusTracker statusTracker,
            BatchJobAdapter batchJobAdapter,
            JobResultCollector resultCollector) {
        this.statusTracker = statusTracker;
        this.batchJobAdapter = batchJobAdapter;
        this.resultCollector = resultCollector;
    }

    public String startJob(String jobId) {
        statusTracker.markSubmitted(jobId);
        boolean accepted = batchJobAdapter.submitBatchJob(jobId);
        if (accepted) {
            statusTracker.markRunning(jobId);
            return jobId;
        }
        statusTracker.markFailed(jobId);
        return jobId;
    }

    public JobStatus statusForJob(String jobId) {
        return statusTracker.statusForJob(jobId);
    }

    public String collectCompletedResult(String jobId) {
        if (statusForJob(jobId) != JobStatus.COMPLETED) {
            return "result-not-ready";
        }
        return resultCollector.collectResult(jobId);
    }
}
