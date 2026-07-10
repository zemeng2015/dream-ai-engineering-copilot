# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field

from dream.security.models import ResourceAccess


class EvidenceNode(BaseModel):
    node_id: str
    node_type: str
    key: str
    title: str
    source_path: str | None = None
    aliases: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class EvidenceEdge(BaseModel):
    edge_id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    confidence: float
    reason: str


class EvidenceGraph(BaseModel):
    graph_id: str
    team_id: str
    repo_name: str | None = None
    built_at: str
    nodes: list[EvidenceNode] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)
    summary: str
    warnings: list[str] = Field(default_factory=list)


class EvidenceGraphSearchResult(BaseModel):
    node: EvidenceNode
    score: int
    reason: str
    matched_terms: list[str] = Field(default_factory=list)
    connected_nodes: list[EvidenceNode] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)


class EvidenceGraphExplainResult(BaseModel):
    query: str
    matched_nodes: list[EvidenceNode] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)
