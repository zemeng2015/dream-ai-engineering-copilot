# SPDX-License-Identifier: Apache-2.0

import hashlib
import re

from dream.codebase.models import DependencyEdge, SymbolNode

CLASS_RE = re.compile(r"\b(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)")
FUNCTION_RE = re.compile(r"\b(?:export\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
METHOD_RE = re.compile(
    r"^\s*(public\s+|private\s+|protected\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.MULTILINE,
)
IMPORT_RE = re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
COMPONENT_RE = re.compile(r"@Component\s*\(")


def extract_typescript(
    relative_path: str, content: str
) -> tuple[list[SymbolNode], list[DependencyEdge]]:
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
    is_component = bool(COMPONENT_RE.search(content))

    for match in CLASS_RE.finditer(content):
        signature = f"class {match.group(1)}"
        if is_component:
            signature = f"@Component {signature}"
        symbols.append(
            _symbol(relative_path, match.group(1), "class", match.start(), content, signature)
        )

    for match in FUNCTION_RE.finditer(content):
        symbols.append(
            _symbol(
                relative_path,
                match.group(1),
                "function",
                match.start(),
                content,
                f"function {match.group(1)}(...)",
            )
        )

    for match in METHOD_RE.finditer(content):
        name = match.group(2)
        if name in {"if", "for", "while", "switch", "catch", "function"}:
            continue
        symbols.append(
            _symbol(relative_path, name, "method", match.start(), content, f"{name}(...)")
        )
    return symbols, dependencies


def _symbol(
    relative_path: str,
    name: str,
    kind: str,
    index: int,
    content: str,
    signature: str,
) -> SymbolNode:
    line = content.count("\n", 0, index) + 1
    return SymbolNode(
        symbol_id=_stable_id(f"{relative_path}:{name}:{line}"),
        name=name,
        kind=kind,
        file_path=relative_path,
        start_line=line,
        signature=signature,
    )


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
