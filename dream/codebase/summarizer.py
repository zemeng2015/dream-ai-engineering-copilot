# SPDX-License-Identifier: Apache-2.0

from dream.codebase.models import FileNode, SymbolNode


def summarize_file(file_node: FileNode) -> str:
    concept_text = _concept_text(file_node.concepts)
    if file_node.role == "test":
        return f"{file_node.language.title()} test file likely covering {concept_text} behavior."
    if file_node.role == "docs":
        return f"Documentation file describing {concept_text}."
    if file_node.role == "config":
        return f"Configuration file for {concept_text}."
    if "controller" in file_node.concepts:
        return f"{file_node.language.title()} controller-like source for {concept_text}."
    if "service" in file_node.concepts:
        return f"{file_node.language.title()} service source related to {concept_text}."
    return f"{file_node.language.title()} {file_node.role} file related to {concept_text}."


def summarize_symbol(symbol: SymbolNode) -> str:
    concept_text = _concept_text(symbol.concepts)
    if symbol.kind == "endpoint":
        return f"API-like endpoint symbol for {concept_text}."
    if symbol.kind == "class":
        return f"Class related to {concept_text}."
    if symbol.kind == "interface":
        return f"Interface related to {concept_text}."
    if symbol.kind == "method":
        return f"Method related to {concept_text}."
    return f"{symbol.kind.title()} symbol related to {concept_text}."


def _concept_text(concepts: list[str]) -> str:
    return ", ".join(concepts[:4]) if concepts else "general repository"
