// SPDX-License-Identifier: Apache-2.0

package com.democorp.demo;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Tracks async job status in memory for local DREAM demos.
 */
public class AsyncJobStatusTracker {
    private final Map<String, JobStatus> statuses = new ConcurrentHashMap<>();

    public void markSubmitted(String jobId) {
        statuses.put(jobId, JobStatus.SUBMITTED);
    }

    public void markRunning(String jobId) {
        statuses.put(jobId, JobStatus.RUNNING);
    }

    public void markCompleted(String jobId) {
        statuses.put(jobId, JobStatus.COMPLETED);
    }

    public void markFailed(String jobId) {
        statuses.put(jobId, JobStatus.FAILED);
    }

    public JobStatus statusForJob(String jobId) {
        return statuses.getOrDefault(jobId, JobStatus.UNKNOWN);
    }
}
