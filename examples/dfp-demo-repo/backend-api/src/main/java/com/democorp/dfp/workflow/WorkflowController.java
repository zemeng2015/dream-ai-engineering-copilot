// SPDX-License-Identifier: Apache-2.0

package com.democorp.dfp.workflow;

/** Synthetic DFP code for DREAM codebase memory demos. */
public class WorkflowController { private final WorkflowService workflowService = new WorkflowService(); public WorkflowDefinition publish(WorkflowDefinition draft) { return workflowService.publishDraft(draft); } }
