# SPDX-License-Identifier: Apache-2.0

import re

from dream.graph.models import (
    EvidenceEdge,
    EvidenceGraph,
    EvidenceGraphExplainResult,
    EvidenceGraphSearchResult,
    EvidenceNode,
)
from dream.graph.repository import EvidenceGraphRepository

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


class EvidenceGraphRetriever:
    def __init__(self, repository: EvidenceGraphRepository | None = None) -> None:
        self.repository = repository or EvidenceGraphRepository()

    def search(
        self,
        *,
        team_id: str,
        query: str,
        repo_name: str | None = None,
        top_k: int = 8,
    ) -> list[EvidenceGraphSearchResult]:
        graph = self._load_best_graph(team_id, repo_name)
        if graph is None:
            return []
        return self.search_graph(graph=graph, query=query, top_k=top_k)

    def search_graph(
        self,
        *,
        graph: EvidenceGraph,
        query: str,
        top_k: int = 8,
    ) -> list[EvidenceGraphSearchResult]:
        terms = self._tokens(query)
        if not terms:
            return []
        node_by_id = {node.node_id: node for node in graph.nodes}
        adjacency = self._adjacency(graph.edges)
        scored: list[tuple[int, str, EvidenceGraphSearchResult]] = []
        for node in graph.nodes:
            score, matched_terms = self._score_node(node, terms, query)
            if score <= 0:
                continue
            connected = self._connected_nodes(node.node_id, node_by_id, adjacency, limit=8)
            paths = self._evidence_paths(node, connected, graph.edges)
            score += self._coverage_bonus(connected)
            scored.append(
                (
                    score,
                    node.title,
                    EvidenceGraphSearchResult(
                        node=node,
                        score=score,
                        reason=(
                            "Evidence graph node matched query terms and expanded "
                            "one-hop related evidence."
                        ),
                        matched_terms=matched_terms,
                        connected_nodes=connected,
                        evidence_paths=paths,
                    ),
                )
            )
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:top_k]]

    def explain(
        self,
        *,
        team_id: str,
        query: str,
        repo_name: str | None = None,
        max_nodes: int = 12,
    ) -> EvidenceGraphExplainResult:
        graph = self._load_best_graph(team_id, repo_name)
        if graph is None:
            return EvidenceGraphExplainResult(query=query)
        results = self.search_graph(graph=graph, query=query, top_k=3)
        node_by_id = {node.node_id: node for node in graph.nodes}
        selected_nodes: dict[str, EvidenceNode] = {}
        selected_edges: dict[str, EvidenceEdge] = {}
        for result in results:
            selected_nodes[result.node.node_id] = result.node
            for connected in result.connected_nodes:
                if len(selected_nodes) >= max_nodes:
                    break
                selected_nodes[connected.node_id] = connected
            for edge in graph.edges:
                if edge.from_node_id in selected_nodes and edge.to_node_id in selected_nodes:
                    selected_edges[edge.edge_id] = edge
        paths = []
        for edge in selected_edges.values():
            from_node = node_by_id.get(edge.from_node_id)
            to_node = node_by_id.get(edge.to_node_id)
            if from_node and to_node:
                paths.append(f"{from_node.title} --{edge.edge_type}--> {to_node.title}")
        return EvidenceGraphExplainResult(
            query=query,
            matched_nodes=sorted(
                selected_nodes.values(),
                key=lambda item: (item.node_type, item.title),
            ),
            edges=sorted(selected_edges.values(), key=lambda item: item.edge_id),
            evidence_paths=sorted(paths),
        )

    def neighbors(
        self,
        *,
        team_id: str,
        node: str,
        repo_name: str | None = None,
        limit: int = 12,
    ) -> EvidenceGraphExplainResult:
        graph = self._load_best_graph(team_id, repo_name)
        if graph is None:
            return EvidenceGraphExplainResult(query=node)
        target = self._resolve_node(graph, node)
        if target is None:
            return EvidenceGraphExplainResult(query=node)
        node_by_id = {item.node_id: item for item in graph.nodes}
        adjacency = self._adjacency(graph.edges)
        connected = self._connected_nodes(target.node_id, node_by_id, adjacency, limit=limit)
        selected_ids = {target.node_id, *(item.node_id for item in connected)}
        selected_edges = [
            edge
            for edge in graph.edges
            if edge.from_node_id in selected_ids and edge.to_node_id in selected_ids
        ]
        return EvidenceGraphExplainResult(
            query=node,
            matched_nodes=[target, *connected],
            edges=selected_edges,
            evidence_paths=self._evidence_paths(target, connected, graph.edges),
        )

    def _load_best_graph(
        self, team_id: str, repo_name: str | None = None
    ) -> EvidenceGraph | None:
        if repo_name is not None:
            return self.repository.try_load(team_id, repo_name)
        graph_names = self.repository.list_graph_names(team_id)
        if not graph_names:
            return None
        return self.repository.try_load(team_id, graph_names[0])

    @staticmethod
    def _adjacency(edges: list[EvidenceEdge]) -> dict[str, list[EvidenceEdge]]:
        adjacency: dict[str, list[EvidenceEdge]] = {}
        for edge in edges:
            adjacency.setdefault(edge.from_node_id, []).append(edge)
            adjacency.setdefault(edge.to_node_id, []).append(edge)
        return adjacency

    @classmethod
    def _connected_nodes(
        cls,
        node_id: str,
        node_by_id: dict[str, EvidenceNode],
        adjacency: dict[str, list[EvidenceEdge]],
        *,
        limit: int,
    ) -> list[EvidenceNode]:
        candidates: list[tuple[int, str, EvidenceNode]] = []
        for edge in adjacency.get(node_id, []):
            other_id = edge.to_node_id if edge.from_node_id == node_id else edge.from_node_id
            other = node_by_id.get(other_id)
            if other is None:
                continue
            candidates.append((cls._node_priority(other), other.title, other))
        candidates.sort(key=lambda item: (item[0], item[1]))
        seen: set[str] = set()
        selected: list[EvidenceNode] = []
        for _, _, node in candidates:
            if node.node_id in seen:
                continue
            seen.add(node.node_id)
            selected.append(node)
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _node_priority(node: EvidenceNode) -> int:
        order = {
            "incident": 0,
            "historical_jira": 1,
            "historical_pr": 2,
            "concept_memory": 3,
            "architecture_doc": 4,
            "domain_doc": 5,
            "code_file": 6,
            "code_symbol": 7,
            "test_file": 8,
            "testing_doc": 9,
            "runbook": 10,
            "concept": 11,
        }
        return order.get(node.node_type, 20)

    @classmethod
    def _score_node(
        cls,
        node: EvidenceNode,
        terms: list[str],
        raw_query: str,
    ) -> tuple[int, list[str]]:
        text = " ".join(
            [
                node.title,
                node.key,
                node.source_path or "",
                " ".join(node.aliases),
                " ".join(node.concepts),
                " ".join(str(value) for value in node.metadata.values()),
            ]
        )
        tokens = cls._tokens(text)
        matched = sorted({term for term in terms if term in tokens})
        score = sum(tokens.count(term) for term in terms)
        if raw_query.lower() in text.lower():
            score += 8
        if node.node_type == "concept" and matched:
            score += 6
        if node.node_type in {"incident", "historical_jira", "historical_pr"} and matched:
            score += 3
        return score, matched

    @staticmethod
    def _coverage_bonus(nodes: list[EvidenceNode]) -> int:
        valuable_types = {
            "incident",
            "historical_jira",
            "historical_pr",
            "code_file",
            "test_file",
            "concept_memory",
        }
        return len({node.node_type for node in nodes if node.node_type in valuable_types})

    @staticmethod
    def _evidence_paths(
        node: EvidenceNode,
        connected: list[EvidenceNode],
        edges: list[EvidenceEdge],
    ) -> list[str]:
        connected_ids = {item.node_id for item in connected}
        paths = []
        for edge in edges:
            if edge.from_node_id == node.node_id and edge.to_node_id in connected_ids:
                target = next(item for item in connected if item.node_id == edge.to_node_id)
                paths.append(f"{node.title} --{edge.edge_type}--> {target.title}")
            elif edge.to_node_id == node.node_id and edge.from_node_id in connected_ids:
                source = next(item for item in connected if item.node_id == edge.from_node_id)
                paths.append(f"{source.title} --{edge.edge_type}--> {node.title}")
        return sorted(paths)

    @staticmethod
    def _resolve_node(graph: EvidenceGraph, value: str) -> EvidenceNode | None:
        normalized = value.strip().lower().replace("\\", "/")
        for node in graph.nodes:
            aliases = {node.key, node.title, node.source_path or "", *node.aliases}
            if normalized in {alias.lower().replace("\\", "/") for alias in aliases if alias}:
                return node
        for node in graph.nodes:
            text = f"{node.title} {node.source_path or ''} {node.key}".lower()
            if normalized in text:
                return node
        return None

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return [token.lower() for token in TOKEN_RE.findall(value)]
