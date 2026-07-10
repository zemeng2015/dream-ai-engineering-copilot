# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field

from dream.security.models import ResourceAccess


class TeamKnowledgePack(BaseModel):
    team_name: str
    team_id: str
    applications: list[str] = Field(default_factory=list)
    repositories: list[str] = Field(default_factory=list)
    document_paths: list[str] = Field(default_factory=list)
    review_rules: list[str] = Field(default_factory=list)
    requirement_template: str = "default"
    test_generation_rules: dict[str, object] = Field(default_factory=dict)
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class Document(BaseModel):
    id: str
    source_path: str
    title: str
    content: str
    metadata: dict[str, str] = Field(default_factory=dict)
    access: ResourceAccess = Field(default_factory=ResourceAccess)


class Chunk(BaseModel):
    id: str
    document_id: str
    source_path: str
    title: str
    content: str
    metadata: dict[str, str] = Field(default_factory=dict)
    access: ResourceAccess = Field(default_factory=ResourceAccess)
