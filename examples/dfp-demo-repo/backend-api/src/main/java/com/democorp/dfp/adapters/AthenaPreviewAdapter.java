// SPDX-License-Identifier: Apache-2.0

package com.democorp.dfp.adapters;

/** Synthetic DFP code for DREAM codebase memory demos. */
public class AthenaPreviewAdapter { public String previewPartition(String executionId, String taskId, int page) { if (executionId == null || taskId == null) { return "missing-partition-predicate"; } return "athena-preview:" + executionId + ":" + taskId + ":page:" + page; } }
