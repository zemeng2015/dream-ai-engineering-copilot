# SPDX-License-Identifier: Apache-2.0

import hashlib
import re

from dream.knowledge.models import Chunk, Document

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


class Chunker:
    def chunk(self, document: Document) -> list[Chunk]:
        sections = self._sections(document.content)
        chunks: list[Chunk] = []
        for index, (title, content) in enumerate(sections):
            chunk_title = title if title != document.title else document.title
            chunk_id = self._stable_id(f"{document.id}:{index}:{chunk_title}")
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    source_path=document.source_path,
                    title=chunk_title,
                    content=content.strip(),
                    metadata=document.metadata.copy(),
                )
            )
        return chunks

    def chunk_all(self, documents: list[Document]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for document in documents:
            chunks.extend(self.chunk(document))
        return chunks

    @staticmethod
    def _sections(content: str) -> list[tuple[str, str]]:
        matches = list(HEADING_RE.finditer(content))
        if not matches:
            return [("Untitled", content)]
        sections: list[tuple[str, str]] = []
        for index, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            section_text = content[start:end].strip()
            if section_text:
                sections.append((title, section_text))
        return sections

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
