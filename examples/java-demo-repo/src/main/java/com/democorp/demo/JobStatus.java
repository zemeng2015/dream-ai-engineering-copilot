// SPDX-License-Identifier: Apache-2.0

package com.democorp.demo;

/**
 * Synthetic status values for the DemoCorp long-running job execution workflow.
 */
public enum JobStatus {
    SUBMITTED,
    RUNNING,
    COMPLETED,
    FAILED,
    UNKNOWN
}
