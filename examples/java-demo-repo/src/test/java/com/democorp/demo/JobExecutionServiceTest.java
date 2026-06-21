// SPDX-License-Identifier: Apache-2.0

package com.democorp.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class JobExecutionServiceTest {
    @Test
    void startsJobAndMarksItRunning() {
        JobExecutionService service = new JobExecutionService();

        String jobId = service.startJob("demo-job-1");

        assertEquals("demo-job-1", jobId);
        assertEquals(JobStatus.RUNNING, service.statusForJob("demo-job-1"));
    }

    @Test
    void returnsUnknownForMissingJob() {
        JobExecutionService service = new JobExecutionService();

        assertEquals(JobStatus.UNKNOWN, service.statusForJob("missing-job"));
    }
}
