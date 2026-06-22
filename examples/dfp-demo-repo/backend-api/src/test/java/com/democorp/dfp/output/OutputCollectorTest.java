// SPDX-License-Identifier: Apache-2.0

package com.democorp.dfp.output;

/** Synthetic test file for DREAM codebase memory. */
class OutputCollectorTest { @Test void retryUsesSameIdempotencyKey() { OutputArtifact artifact = new OutputCollector().collectForExecution("exec-1", "task-1", "attempt-1"); assertEquals("exec-1:task-1:attempt-1", artifact.idempotencyKey); } }
