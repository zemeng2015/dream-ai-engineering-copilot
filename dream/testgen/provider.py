# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from dream.testgen.models import TestGenPlan, TestGenRequest, TestGenResult


class TestGenProvider(Protocol):
    provider_name: str

    def plan(self, request: TestGenRequest) -> TestGenPlan:
        """Create a test-generation plan."""

    def run(self, request: TestGenRequest) -> TestGenResult:
        """Run or simulate test generation."""

