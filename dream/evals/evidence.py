# SPDX-License-Identifier: Apache-2.0

import re

import yaml

from dream.core.errors import NotFoundError
from dream.core.paths import get_knowledge_packs_dir
from dream.evals.models import EvalProfile


class EvidenceCoverageAnalyzer:
    def analyze(self, markdown: str, sources: list[str] | None = None) -> dict[str, bool]:
        source_text = "\n".join(sources or [])
        text = f"{markdown}\n{source_text}".lower()
        coverage = {
            "domain_docs": self._has_any(
                text, ["docs/domain", "job-lifecycle.md", "workflow-model.md"]
            ),
            "architecture_docs": self._has_any(
                text,
                ["docs/architecture", "architecture", "status-tracking-design.md"],
            ),
            "runbooks": self._has_any(text, ["docs/runbooks", "runbook"]),
            "incidents": bool(re.search(r"\binc-\d{3}\b", text)) or "docs/incidents" in text,
            "historical_jira": bool(re.search(r"\bdfp-\d{3}\b", text))
            or "docs/historical-jira" in text,
            "historical_pr": bool(re.search(r"\bpr-\d{3}\b", text)) or "docs/historical-pr" in text,
            "testing_docs": self._has_any(text, ["docs/testing", "test plan", "regression-test"]),
            "concept_memory": self._has_any(
                text, ["docs/concepts", "concept memory", "-memory.md"]
            ),
            "code_files": bool(re.search(r"[\w\-/]+(\.java|\.ts|\.py|\.json)\b", text)),
            "test_files": bool(
                re.search(r"(src/test|tests/|test_[\w-]+\.py|[\w-]+test\.java|\.spec\.ts)", text)
            ),
        }
        if self._has_any(
            text,
            [
                "evidence graph",
                "evidence-graph#",
                "graph_",
                "memory graph",
                "--implemented_by-->",
                "--tested_by-->",
                "--regressed_by-->",
            ],
        ):
            coverage["evidence_graph"] = True
        return coverage

    @staticmethod
    def _has_any(text: str, values: list[str]) -> bool:
        return any(value.lower() in text for value in values)


class EvalProfileLoader:
    def load(self, team_id: str, profile_id: str) -> EvalProfile:
        if "/" in profile_id or "\\" in profile_id or ".." in profile_id:
            raise NotFoundError(f"Invalid eval profile id: {profile_id}")
        path = get_knowledge_packs_dir() / team_id / "eval_profiles" / f"{profile_id}.yaml"
        if not path.exists():
            raise NotFoundError(f"Eval profile not found: {team_id}/{profile_id}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return EvalProfile.model_validate(data)

    def list(self, team_id: str) -> list[EvalProfile]:
        profile_dir = get_knowledge_packs_dir() / team_id / "eval_profiles"
        if not profile_dir.exists():
            return []
        return [
            self.load(team_id, path.stem)
            for path in sorted(profile_dir.glob("*.yaml"))
            if path.is_file()
        ]

    def infer(self, team_id: str, text: str) -> EvalProfile | None:
        normalized = text.lower()
        best_profile: EvalProfile | None = None
        best_score = 0
        for profile in self.list(team_id):
            score = sum(1 for pattern in profile.query_patterns if pattern.lower() in normalized)
            score += sum(
                1 for concept in profile.expected_concepts if concept.lower() in normalized
            )
            if score > best_score:
                best_score = score
                best_profile = profile
        return best_profile if best_score > 0 else None
