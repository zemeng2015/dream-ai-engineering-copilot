// SPDX-License-Identifier: Apache-2.0

package com.democorp.dfp.output;

/** Synthetic test file for DREAM codebase memory. */
class OutputPreviewServiceTest { @Test void largeArtifactUsesPartitionPreview() { OutputArtifact artifact = new OutputArtifact(); artifact.executionId = "exec-1"; artifact.taskId = "task-1"; artifact.sizeBytes = 1500000000L; assertEquals("athena-preview:exec-1:task-1:page:1", new OutputPreviewService().preview(artifact, 1)); } }
