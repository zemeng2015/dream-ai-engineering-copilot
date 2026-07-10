# SPDX-License-Identifier: Apache-2.0

import hashlib
from pathlib import Path

import yaml

from dream.core.errors import PathTraversalError
from dream.core.paths import display_path
from dream.dlp import DefaultDlpEngine
from dream.knowledge.models import Document, TeamKnowledgePack
from dream.security.models import ResourceAccess


class MarkdownDocumentLoader:
    _DLP_METADATA_SEPARATOR = "\n__DREAM_DLP_METADATA_BOUNDARY__\n"

    def __init__(self, *, dlp_engine: DefaultDlpEngine | None = None) -> None:
        self.dlp_engine = dlp_engine or DefaultDlpEngine()

    def load_for_pack(self, pack: TeamKnowledgePack, pack_dir: Path) -> list[Document]:
        documents: list[Document] = []
        for relative_doc_dir in pack.document_paths:
            doc_dir = self._resolve_document_dir(pack_dir, relative_doc_dir)
            if not doc_dir.exists():
                continue
            for path in sorted(doc_dir.rglob("*.md")):
                documents.append(self.load(path, team_id=pack.team_id, pack_dir=pack_dir))
        return documents

    def load(self, path: Path, *, team_id: str, pack_dir: Path | None = None) -> Document:
        raw = path.read_text(encoding="utf-8")
        metadata, content = self._split_front_matter(raw)
        candidate_metadata = {
            "team_id": team_id,
            "app": str(metadata.get("app", "")),
            "component": str(metadata.get("component", "")),
            "doc_type": str(metadata.get("doc_type") or self._infer_doc_type(path, pack_dir)),
        }
        source_path = display_path(path)
        access = ResourceAccess.from_metadata(metadata)
        metadata_keys = ["app", "component", "doc_type"]
        metadata_inspection = self.dlp_engine.enforce(
            self._DLP_METADATA_SEPARATOR.join(candidate_metadata[key] for key in metadata_keys),
            stage="pre_index",
            team_id=team_id,
            resource_id=f"{source_path}:index-metadata",
            classification=access.classification,
        )
        sanitized_values = metadata_inspection.sanitized_text.split(
            self._DLP_METADATA_SEPARATOR
        )
        if len(sanitized_values) != len(metadata_keys):
            raise RuntimeError("DLP metadata boundary was not preserved during inspection.")
        base_metadata = {
            **candidate_metadata,
            **dict(zip(metadata_keys, sanitized_values, strict=True)),
        }
        inspection = self.dlp_engine.enforce(
            content,
            stage="pre_index",
            team_id=team_id,
            resource_id=source_path,
            classification=access.classification,
        )
        title = (
            self._extract_title(inspection.sanitized_text)
            or path.stem.replace("-", " ").title()
        )
        base_metadata["dlp_policy_version"] = inspection.evidence.policy_version
        base_metadata["dlp_redaction_count"] = str(
            metadata_inspection.evidence.redaction_count + inspection.evidence.redaction_count
        )
        return Document(
            id=self._stable_id(source_path),
            source_path=source_path,
            title=title,
            content=inspection.sanitized_text.strip(),
            metadata=base_metadata,
            access=access,
        )

    @staticmethod
    def _split_front_matter(raw: str) -> tuple[dict[str, object], str]:
        candidate = MarkdownDocumentLoader._drop_leading_html_comments(raw)
        if not candidate.startswith("---\n"):
            return {}, candidate
        parts = candidate.split("---\n", 2)
        if len(parts) != 3:
            return {}, candidate
        metadata = yaml.safe_load(parts[1]) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return metadata, parts[2]

    @staticmethod
    def _drop_leading_html_comments(raw: str) -> str:
        remaining = raw.lstrip()
        while remaining.startswith("<!--"):
            end_index = remaining.find("-->")
            if end_index == -1:
                return remaining
            remaining = remaining[end_index + 3 :].lstrip()
        return remaining

    @staticmethod
    def _extract_title(content: str) -> str | None:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return None

    @staticmethod
    def _infer_doc_type(path: Path, pack_dir: Path | None) -> str:
        if pack_dir is None:
            return path.parent.name
        try:
            relative_parts = path.relative_to(pack_dir / "docs").parts
        except ValueError:
            return path.parent.name
        return relative_parts[0] if relative_parts else path.parent.name

    @staticmethod
    def _resolve_document_dir(pack_dir: Path, relative_doc_dir: str) -> Path:
        pack_root = pack_dir.resolve()
        doc_dir = (pack_root / relative_doc_dir).resolve()
        if not doc_dir.is_relative_to(pack_root):
            raise PathTraversalError(
                f"Knowledge document path escapes pack directory: {relative_doc_dir}"
            )
        return doc_dir

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
