// SPDX-License-Identifier: Apache-2.0

package com.democorp.demo;

/**
 * Synthetic result collector for completed DemoCorp job executions.
 */
public class JobResultCollector {
    public String collectResult(String jobId) {
        return "result-for-" + jobId;
    }

    public boolean hasResult(String jobId) {
        return jobId != null && !jobId.isBlank();
    }
}
