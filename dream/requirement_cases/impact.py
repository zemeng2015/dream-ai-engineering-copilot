# SPDX-License-Identifier: Apache-2.0

import hashlib

from dream.requirement_cases.models import ContextEvidence, ImpactItem, RequirementCase


class ImpactMapGenerator:
    def generate(self, case: RequirementCase, evidence: list[ContextEvidence]) -> list[ImpactItem]:
        request = case.raw_request.lower()
        items: list[ImpactItem] = []
        if "job" in request or "execution" in request:
            items.append(
                self._item(
                    case,
                    "workflow",
                    "Long-running job execution workflow",
                    "The request changes how submitted jobs move through execution and "
                    "status states.",
                    0.86,
                    evidence,
                    ["job execution", "workflow"],
                )
            )
        if self._has(evidence, ["Service", "Tracker", "Adapter", "Collector"]):
            items.append(
                self._item(
                    case,
                    "backend",
                    "Job execution backend services",
                    "Service, tracker, adapter, or collector classes may need behavior changes.",
                    0.84,
                    evidence,
                    ["Service", "Tracker", "Adapter", "Collector"],
                )
            )
        if self._has(evidence, ["Controller", "endpoint"]):
            items.append(
                self._item(
                    case,
                    "api",
                    "Job execution API contract",
                    "Controller-like endpoints may need status response or polling "
                    "contract updates.",
                    0.78,
                    evidence,
                    ["Controller", "endpoint", "api"],
                )
            )
        if "status" in request or self._has(evidence, ["JobStatus", "status"]):
            items.append(
                self._item(
                    case,
                    "data",
                    "Job status model",
                    "Status values and transitions should be explicit and testable.",
                    0.76,
                    evidence,
                    ["JobStatus", "status"],
                )
            )
        if self._has(evidence, ["Test", "test"]):
            items.append(
                self._item(
                    case,
                    "test",
                    "Job execution regression tests",
                    "Existing or likely tests should cover submitted, running, completed, "
                    "and failed states.",
                    0.82,
                    evidence,
                    ["Test", "test"],
                )
            )
        if self._has(evidence, ["runbook", "failure", "BatchJobAdapter"]):
            items.append(
                self._item(
                    case,
                    "ops",
                    "Batch job failure operations",
                    "Runbook and adapter behavior may need monitoring, retry, and "
                    "timeout guidance.",
                    0.68,
                    evidence,
                    ["runbook", "failure", "BatchJobAdapter"],
                )
            )
        if "status" in request:
            items.append(
                ImpactItem(
                    impact_id=self._stable_id(f"{case.case_id}:frontend:status-display"),
                    case_id=case.case_id,
                    area_type="frontend",
                    name="Possible status display",
                    description=(
                        "No direct frontend code evidence was required, but users may need visible "
                        "pending/running/completed/failed states."
                    ),
                    confidence=0.45,
                    sources=[],
                    reason=(
                        "Inferred from status tracking request; confirm UI ownership with FE/BA."
                    ),
                )
            )
        return self._dedupe(items)

    def _item(
        self,
        case: RequirementCase,
        area_type: str,
        name: str,
        description: str,
        confidence: float,
        evidence: list[ContextEvidence],
        markers: list[str],
    ) -> ImpactItem:
        sources = self._matching_sources(evidence, markers)
        return ImpactItem(
            impact_id=self._stable_id(f"{case.case_id}:{area_type}:{name}"),
            case_id=case.case_id,
            area_type=area_type,
            name=name,
            description=description,
            confidence=confidence,
            sources=sources,
            reason=f"Matched evidence markers: {', '.join(markers)}.",
        )

    @staticmethod
    def _has(evidence: list[ContextEvidence], markers: list[str]) -> bool:
        joined = "\n".join(
            f"{item.source_path} {item.title} {item.excerpt} {item.reason}" for item in evidence
        ).lower()
        return any(marker.lower() in joined for marker in markers)

    @staticmethod
    def _matching_sources(evidence: list[ContextEvidence], markers: list[str]) -> list[str]:
        sources: list[str] = []
        for item in evidence:
            text = f"{item.source_path} {item.title} {item.excerpt} {item.reason}".lower()
            if any(marker.lower() in text for marker in markers):
                sources.extend(item.provenance_paths())
        return sorted(dict.fromkeys(sources))

    @staticmethod
    def _dedupe(items: list[ImpactItem]) -> list[ImpactItem]:
        seen: set[tuple[str, str]] = set()
        result: list[ImpactItem] = []
        for item in items:
            key = (item.area_type, item.name)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
