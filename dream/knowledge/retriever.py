# SPDX-License-Identifier: Apache-2.0

import re

from dream.knowledge.models import Chunk

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
    "without",
}


class SimpleRetriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks

    def search(
        self,
        query: str,
        *,
        team_id: str | None = None,
        app: str | None = None,
        component: str | None = None,
        doc_type: str | None = None,
        top_k: int = 5,
    ) -> list[Chunk]:
        return [
            chunk
            for _, chunk in self.search_scored(
                query,
                team_id=team_id,
                app=app,
                component=component,
                doc_type=doc_type,
                top_k=top_k,
            )
        ]

    def search_scored(
        self,
        query: str,
        *,
        team_id: str | None = None,
        app: str | None = None,
        component: str | None = None,
        doc_type: str | None = None,
        top_k: int = 5,
    ) -> list[tuple[int, Chunk]]:
        terms = self._tokens(query)
        scored: list[tuple[int, str, str, Chunk]] = []
        for chunk in self.chunks:
            if not self._metadata_matches(
                chunk, team_id=team_id, app=app, component=component, doc_type=doc_type
            ):
                continue
            score = self._score(chunk, terms)
            if score > 0:
                scored.append((score, chunk.title.lower(), chunk.source_path, chunk))
        scored.sort(key=lambda item: (-item[0], item[1], item[2], item[3].id))
        return [(item[0], item[3]) for item in scored[:top_k]]

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return [
            token.lower()
            for token in TOKEN_RE.findall(value)
            if token.lower() not in STOP_WORDS
        ]

    @classmethod
    def _score(cls, chunk: Chunk, terms: list[str]) -> int:
        title_tokens = cls._tokens(chunk.title)
        content_tokens = cls._tokens(chunk.content)
        return sum(title_tokens.count(term) * 3 + content_tokens.count(term) for term in terms)

    @staticmethod
    def _metadata_matches(
        chunk: Chunk,
        *,
        team_id: str | None,
        app: str | None,
        component: str | None,
        doc_type: str | None,
    ) -> bool:
        filters = {
            "team_id": team_id,
            "app": app,
            "component": component,
            "doc_type": doc_type,
        }
        for key, expected in filters.items():
            if expected is not None and chunk.metadata.get(key) != expected:
                return False
        return True
