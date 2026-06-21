package com.democorp.dfp.output;

/** Synthetic DFP code for DREAM codebase memory demos. */
public class OutputPreviewService { private final StorageAdapter storageAdapter = new StorageAdapter(); private final AthenaPreviewAdapter athenaPreviewAdapter = new AthenaPreviewAdapter(); public String preview(OutputArtifact artifact, int page) { if (artifact.sizeBytes > 100000000L) { return athenaPreviewAdapter.previewPartition(artifact.executionId, artifact.taskId, page); } return storageAdapter.previewSmallObject(artifact.storageKey, page); } }
