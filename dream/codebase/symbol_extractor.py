# SPDX-License-Identifier: Apache-2.0

import re
from pathlib import Path

from dream.codebase.java_extractor import extract_java
from dream.codebase.models import DependencyEdge, SymbolNode
from dream.codebase.python_extractor import extract_python
from dream.codebase.typescript_extractor import extract_typescript

CAMEL_RE = re.compile(r"(?<!^)(?=[A-Z])")
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9]*")

KEY_PHRASES = [
    "async status",
    "status tracking",
    "job execution",
    "long running job",
    "batch job",
    "job status",
    "result collection",
    "failure handling",
]

IMPORTANT_TOKENS = {
    "api",
    "async",
    "batch",
    "collector",
    "component",
    "controller",
    "execution",
    "failure",
    "job",
    "result",
    "service",
    "status",
    "test",
    "tracker",
    "workflow",
}


def extract_symbols_and_dependencies(
    *,
    language: str,
    path: Path,
    relative_path: str,
    content: str | None = None,
) -> tuple[list[SymbolNode], list[DependencyEdge], list[str]]:
    content = content if content is not None else path.read_text(encoding="utf-8")
    if language == "java":
        symbols, dependencies = extract_java(relative_path, content)
    elif language == "python":
        symbols, dependencies = extract_python(relative_path, content)
    elif language == "typescript":
        symbols, dependencies = extract_typescript(relative_path, content)
    else:
        symbols, dependencies = [], []
    concepts = derive_concepts(relative_path, content, [symbol.name for symbol in symbols])
    return symbols, dependencies, concepts


def derive_concepts(path: str, content: str, symbol_names: list[str] | None = None) -> list[str]:
    source = f"{path} {content[:8000]} {' '.join(symbol_names or [])}".lower()
    concepts: set[str] = set()
    for phrase in KEY_PHRASES:
        if all(part in source for part in phrase.split()):
            concepts.add(phrase)

    tokens = _tokens(path)
    for symbol_name in symbol_names or []:
        tokens.extend(_tokens(symbol_name))

    for token in tokens:
        if token in IMPORTANT_TOKENS:
            concepts.add(token)

    token_set = set(tokens)
    if {"job", "execution"} <= token_set:
        concepts.add("job execution")
    if {"job", "status"} <= token_set:
        concepts.add("job status")
    if {"async", "job"} <= token_set:
        concepts.add("async job")
    if {"status", "tracker"} <= token_set or {"status", "tracking"} <= token_set:
        concepts.add("status tracking")
    if {"batch", "job"} <= token_set:
        concepts.add("batch job")
    if {"result", "collector"} <= token_set:
        concepts.add("result collection")
    return sorted(concepts)


def concepts_for_symbol(symbol: SymbolNode, file_concepts: list[str]) -> list[str]:
    symbol_tokens = set(_tokens(symbol.name))
    concepts = set(file_concepts)
    for token in symbol_tokens:
        if token in IMPORTANT_TOKENS:
            concepts.add(token)
    if {"job", "execution"} <= symbol_tokens:
        concepts.add("job execution")
    if {"job", "status"} <= symbol_tokens:
        concepts.add("job status")
    if {"status", "tracker"} <= symbol_tokens:
        concepts.add("status tracking")
    return sorted(concepts)


def _tokens(value: str) -> list[str]:
    normalized = value.replace("-", " ").replace("_", " ").replace("/", " ").replace(".", " ")
    raw_tokens: list[str] = []
    for token in TOKEN_RE.findall(normalized):
        raw_tokens.extend(CAMEL_RE.sub(" ", token).split())
    return [token.lower() for token in raw_tokens if len(token) > 1]
