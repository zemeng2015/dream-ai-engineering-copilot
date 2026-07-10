# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from pydantic import BaseModel

from dream.context.models import ContextPack, MemoryMapReport, PromptPreview, RetrievalTrail
from dream.core.paths import display_path, resolve_artifact_path


class ContextArtifactRepository:
    def save_trail(self, trail: RetrievalTrail) -> RetrievalTrail:
        base = self._base_dir("context-trails") / self._safe_name(trail.trail_id)
        return self._save_pair(trail, base, self._trail_markdown(trail))

    def save_context_pack(self, pack: ContextPack) -> ContextPack:
        base = self._base_dir("context-packs") / self._safe_name(pack.context_pack_id)
        return self._save_pair(pack, base, self._pack_markdown(pack))

    def save_prompt_preview(self, preview: PromptPreview) -> PromptPreview:
        base = self._base_dir("prompt-previews") / self._safe_name(preview.preview_id)
        return self._save_pair(preview, base, self._prompt_markdown(preview))

    def save_memory_report(self, report: MemoryMapReport) -> MemoryMapReport:
        base = self._base_dir("memory-map-reports") / self._safe_name(report.report_id)
        return self._save_pair(report, base, self._memory_report_markdown(report))

    def load_trail(self, trail_id: str) -> RetrievalTrail:
        path = self._base_dir("context-trails") / self._safe_name(trail_id) / "trail.json"
        return RetrievalTrail.model_validate_json(path.read_text(encoding="utf-8"))

    def load_context_pack(self, context_pack_id: str) -> ContextPack:
        path = (
            self._base_dir("context-packs")
            / self._safe_name(context_pack_id)
            / "context-pack.json"
        )
        return ContextPack.model_validate_json(path.read_text(encoding="utf-8"))

    def load_prompt_preview(self, preview_id: str) -> PromptPreview:
        path = (
            self._base_dir("prompt-previews")
            / self._safe_name(preview_id)
            / "prompt-preview.json"
        )
        return PromptPreview.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _base_dir(name: str) -> Path:
        path = resolve_artifact_path(name)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _save_pair(model: BaseModel, base: Path, markdown: str):
        base.mkdir(parents=True, exist_ok=True)
        json_path = base / _json_name(model)
        markdown_path = base / _markdown_name(model)
        updated = model.model_copy(
            update={
                "json_path": display_path(json_path),
                "markdown_path": display_path(markdown_path),
            }
        )
        json_path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
        markdown_path.write_text(markdown, encoding="utf-8")
        return updated

    @staticmethod
    def _safe_name(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace("..", "_")

    @staticmethod
    def _trail_markdown(trail: RetrievalTrail) -> str:
        lines = [
            "# Retrieval Trail",
            "",
            f"- Trail: `{trail.trail_id}`",
            f"- Team: `{trail.team_id}`",
            f"- Repo: `{trail.repo_name or '_team'}`",
            f"- Query: {trail.raw_query}",
            f"- Concepts: {', '.join(trail.detected_concepts) or 'none'}",
            "",
            "## Steps",
        ]
        for step in trail.retrieval_steps:
            lines.append(
                f"- {step.step_name}: {step.selected_count}/{step.candidates_found} selected"
            )
        lines.extend(["", "## Selected Evidence"])
        lines.extend(_evidence_lines(trail.selected_evidence))
        lines.extend(["", "## Graph Paths"])
        lines.extend(f"- {item.path}" for item in trail.graph_expansion_paths or [])
        lines.extend(["", "## Memory Claims"])
        lines.extend(
            f"- `{item.claim_id}` `{item.status}` {item.entity} --{item.relation}--> "
            f"{item.value or '_'}; reviewed by {item.reviewed_by or 'unknown'} "
            f"at {item.reviewed_at or 'unknown'}"
            for item in trail.memory_claims_considered
        )
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in trail.warnings or ["None."])
        lines.extend(["", "## Final Context Summary", trail.final_context_summary])
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _pack_markdown(pack: ContextPack) -> str:
        lines = [
            "# Context Pack",
            "",
            f"- Context pack: `{pack.context_pack_id}`",
            f"- Team: `{pack.team_id}`",
            f"- Repo: `{pack.repo_name or '_team'}`",
            f"- Selected evidence: {pack.selected_evidence_count}",
            f"- Budget: {pack.deterministic_size_budget}",
            "",
            "## User Request",
            pack.user_request,
            "",
            "## Documents",
            *_evidence_lines(pack.selected_docs),
            "",
            "## Code",
            *_evidence_lines(pack.selected_code),
            "",
            "## Tests",
            *_evidence_lines(pack.selected_tests),
            "",
            "## Incidents",
            *_evidence_lines(pack.selected_incidents),
            "",
            "## Historical Jira / PR",
            *_evidence_lines(pack.selected_historical_jira + pack.selected_historical_pr),
            "",
            "## Memory Claims",
        ]
        lines.extend(
            f"- `{item.claim_id}` `{item.status}` {item.entity} --{item.relation}--> "
            f"{item.value or '_'}; reviewed by {item.reviewed_by or 'unknown'} "
            f"at {item.reviewed_at or 'unknown'}"
            for item in pack.selected_memory_claims
        )
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in pack.warnings or ["None."])
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _prompt_markdown(preview: PromptPreview) -> str:
        sources = "\n".join(f"- {path}" for path in preview.evidence_paths) or "- None"
        warnings = "\n".join(f"- {warning}" for warning in preview.warnings) or "- None"
        return f"""# Prompt Preview

- Preview: `{preview.preview_id}`
- Target: `{preview.target}`
- Provider mode: `{preview.provider_mode}`

## Evidence Paths
{sources}

## Warnings
{warnings}

## Prompt
```text
{preview.prompt_text}
```
"""

    @staticmethod
    def _memory_report_markdown(report: MemoryMapReport) -> str:
        lines = [
            "# Graph / Memory Report",
            "",
            f"- Team: `{report.team_id}`",
            f"- Repo: `{report.repo_name or '_team'}`",
            f"- Approved claims: {report.approved_memory_claims}",
            f"- Candidate claims: {report.candidate_memory_claims}",
            "",
            "## Top Concepts",
            *(f"- {item}" for item in report.top_concepts or ["None"]),
            "",
            "## Important Paths",
            *(f"- {item}" for item in report.important_paths or ["None"]),
            "",
            "## Missing Test Links",
            *(f"- {item}" for item in report.missing_test_links or ["None"]),
            "",
            "## Recommendations",
            *(f"- {item}" for item in report.recommendations or ["None"]),
        ]
        return "\n".join(lines).rstrip() + "\n"


def _evidence_lines(items) -> list[str]:
    if not items:
        return ["- None"]
    return [
        f"- {item.title} [{item.source_type}] ({item.source_path}) score={item.score:.2f} "
        f"- {item.reason}"
        for item in items
    ]


def _json_name(model: BaseModel) -> str:
    if isinstance(model, RetrievalTrail):
        return "trail.json"
    if isinstance(model, ContextPack):
        return "context-pack.json"
    if isinstance(model, PromptPreview):
        return "prompt-preview.json"
    return "report.json"


def _markdown_name(model: BaseModel) -> str:
    if isinstance(model, RetrievalTrail):
        return "trail.md"
    if isinstance(model, ContextPack):
        return "context-pack.md"
    if isinstance(model, PromptPreview):
        return "prompt-preview.md"
    return "report.md"
