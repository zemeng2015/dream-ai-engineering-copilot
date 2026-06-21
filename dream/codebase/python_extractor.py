# SPDX-License-Identifier: Apache-2.0

import ast
import hashlib

from dream.codebase.models import DependencyEdge, SymbolNode


def extract_python(
    relative_path: str, content: str
) -> tuple[list[SymbolNode], list[DependencyEdge]]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return [], []

    symbols: list[SymbolNode] = []
    dependencies: list[DependencyEdge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(
                SymbolNode(
                    symbol_id=_stable_id(f"{relative_path}:{node.name}:class"),
                    name=node.name,
                    kind="class",
                    file_path=relative_path,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", None),
                    signature=f"class {node.name}",
                    docstring=ast.get_docstring(node),
                )
            )
        elif isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            symbols.append(
                SymbolNode(
                    symbol_id=_stable_id(f"{relative_path}:{node.name}:{node.lineno}"),
                    name=node.name,
                    kind="function",
                    file_path=relative_path,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", None),
                    signature=f"{prefix} {node.name}(...)",
                    docstring=ast.get_docstring(node),
                )
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                dependencies.append(
                    DependencyEdge(
                        from_file=relative_path,
                        to_symbol=alias.name,
                        dependency_type="import",
                        confidence=0.6,
                    )
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            dependencies.append(
                DependencyEdge(
                    from_file=relative_path,
                    to_symbol=node.module,
                    dependency_type="import",
                    confidence=0.6,
                )
            )
    return symbols, dependencies


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
