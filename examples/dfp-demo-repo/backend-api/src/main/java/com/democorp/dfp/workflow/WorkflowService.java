// SPDX-License-Identifier: Apache-2.0

package com.democorp.dfp.workflow;

/** Synthetic DFP code for DREAM codebase memory demos. */
public class WorkflowService { public WorkflowDefinition publishDraft(WorkflowDefinition draft) { draft.published = true; return draft; } public boolean canEditInPlace(WorkflowDefinition workflowDefinition) { return workflowDefinition != null && !workflowDefinition.published; } }
