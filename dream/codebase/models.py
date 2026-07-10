# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field

from dream.security.models import ResourceAccess


class FileNode(BaseModel):
    file_id: str
    path: str
    language: str
    size_bytes: int
    line_count: int
    role: str
    summary: str | None = None
    symbols: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class SymbolNode(BaseModel):
    symbol_id: str
    name: str
    kind: str
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    signature: str | None = None
    docstring: str | None = None
    summary: str | None = None
    concepts: list[str] = Field(default_factory=list)
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class TestMapping(BaseModel):
    source_file: str
    test_file: str
    confidence: float
    reason: str
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class DependencyEdge(BaseModel):
    from_symbol: str | None = None
    from_file: str
    to_symbol: str | None = None
    to_file: str | None = None
    dependency_type: str
    confidence: float


class ConceptMapping(BaseModel):
    concept: str
    related_files: list[str] = Field(default_factory=list)
    related_symbols: list[str] = Field(default_factory=list)
    related_tests: list[str] = Field(default_factory=list)
    related_docs: list[str] = Field(default_factory=list)
    confidence: float
    reason: str
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class RepoIndex(BaseModel):
    repo_id: str
    repo_name: str
    repo_path: str
    team_id: str
    indexed_at: str
    files: list[FileNode] = Field(default_factory=list)
    symbols: list[SymbolNode] = Field(default_factory=list)
    tests: list[TestMapping] = Field(default_factory=list)
    dependencies: list[DependencyEdge] = Field(default_factory=list)
    concepts: list[ConceptMapping] = Field(default_factory=list)
    summary: str
    warnings: list[str] = Field(default_factory=list)
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class CodebaseSearchResult(BaseModel):
    result_type: str
    title: str
    source_path: str
    excerpt: str
    score: int
    reason: str
    metadata: dict[str, str] = Field(default_factory=dict)
    access: ResourceAccess = Field(default_factory=ResourceAccess)
