// SPDX-License-Identifier: Apache-2.0

package com.democorp.demo;

/**
 * API-like controller for the synthetic DemoCorp job execution workflow.
 */
@RestController
@RequestMapping("/demo/jobs")
public class JobExecutionController {
    private final JobExecutionService jobExecutionService;

    public JobExecutionController(JobExecutionService jobExecutionService) {
        this.jobExecutionService = jobExecutionService;
    }

    @PostMapping("/{jobId}/start")
    public String startJob(String jobId) {
        return jobExecutionService.startJob(jobId);
    }

    @GetMapping("/{jobId}/status")
    public JobStatus getJobStatus(String jobId) {
        return jobExecutionService.statusForJob(jobId);
    }
}
