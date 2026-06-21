// SPDX-License-Identifier: Apache-2.0

package com.democorp.demo;

/**
 * Fake adapter boundary for launching a long-running batch job.
 */
public class BatchJobAdapter {
    public boolean submitBatchJob(String jobId) {
        return jobId != null && !jobId.isBlank();
    }

    public boolean shouldRetry(String jobId, int attemptCount) {
        return jobId != null && attemptCount < 3;
    }
}
