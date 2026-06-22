// SPDX-License-Identifier: Apache-2.0

package com.democorp.dfp.execution;

/** Synthetic test file for DREAM codebase memory. */
class ExecutionServiceTest { @Test void resolvesPartialSuccessWhenOnlyOptionalTaskFails() { assertEquals(ExecutionStatus.PARTIAL_SUCCESS, new ExecutionService().resolveFinalStatus(false, true)); } }
