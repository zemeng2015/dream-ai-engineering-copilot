// SPDX-License-Identifier: Apache-2.0

package com.democorp.dfp.execution;

/** Synthetic test file for DREAM codebase memory. */
class StatusTrackerTest { @Test void queuedExecutionIsNotStaleRunning() { StatusTracker tracker = new StatusTracker(); tracker.markExecutionQueued("exec-1"); assertFalse(tracker.isStaleRunning("exec-1", Instant.now())); } }
