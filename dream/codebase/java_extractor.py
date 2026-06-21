# SPDX-License-Identifier: Apache-2.0

import hashlib
import re

from dream.codebase.models import DependencyEdge, SymbolNode

CLASS_RE = re.compile(r"\b(public\s+)?(class|interface)\s+([A-Za-z_][A-Za-z0-9_]*)")
IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_.*]+)\s*;", re.MULTILINE)
METHOD_RE = re.compile(
    r"^\s*(public|protected|private)?\s*(static\s+)?"
    r"([A-Za-z0-9_<>, ?\[\]]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\(([^;{}]*)\)\s*(?:throws\s+[A-Za-z0-9_, ]+\s*)?\{",
    re.MULTILINE,
)
ANNOTATION_RE = re.compile(r"^\s*@([A-Za-z_][A-Za-z0-9_]*)(?:\(([^)]*)\))?", re.MULTILINE)
ENDPOINT_ANNOTATIONS = {
    "GetMapping",
    "PostMapping",
    "PutMapping",
    "DeleteMapping",
    "RequestMapping",
}


def extract_java(relative_path: str, content: str) -> tuple[list[SymbolNode], list[DependencyEdge]]:
    symbols: list[SymbolNode] = []
    dependencies = [
        DependencyEdge(
            from_file=relative_path,
            to_symbol=match.group(1),
            dependency_type="import",
            confidence=0.6,
        )
        for match in IMPORT_RE.finditer(content)
    ]

    for match in CLASS_RE.finditer(content):
        kind = "interface" if match.group(2) == "interface" else "class"
        symbols.append(
            SymbolNode(
                symbol_id=_stable_id(f"{relative_path}:{match.group(3)}:{kind}"),
                name=match.group(3),
                kind=kind,
                file_path=relative_path,
                start_line=_line_number(content, match.start()),
                signature=match.group(0).strip(),
                docstring=_leading_comment(content, match.start()),
            )
        )

    annotations_by_line = _annotations_by_line(content)
    for match in METHOD_RE.finditer(content):
        method_name = match.group(4)
        if method_name in {"if", "for", "while", "switch", "catch"}:
            continue
        start_line = _line_number(content, match.start())
        annotations = annotations_by_line.get(start_line - 1, []) + annotations_by_line.get(
            start_line - 2, []
        )
        kind = "endpoint" if any(name in ENDPOINT_ANNOTATIONS for name in annotations) else "method"
        signature = " ".join(match.group(0).strip().split())
        symbols.append(
            SymbolNode(
                symbol_id=_stable_id(f"{relative_path}:{method_name}:{start_line}"),
                name=method_name,
                kind=kind,
                file_path=relative_path,
                start_line=start_line,
                signature=signature.rstrip("{").strip(),
                docstring=_leading_comment(content, match.start()),
            )
        )
    return symbols, dependencies


def _annotations_by_line(content: str) -> dict[int, list[str]]:
    annotations: dict[int, list[str]] = {}
    for match in ANNOTATION_RE.finditer(content):
        line = _line_number(content, match.start())
        annotations.setdefault(line, []).append(match.group(1))
    return annotations


def _line_number(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def _leading_comment(content: str, index: int) -> str | None:
    prefix = content[:index].rstrip()
    if prefix.endswith("*/"):
        start = prefix.rfind("/**")
        if start != -1:
            return prefix[start:].strip()
    return None


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
