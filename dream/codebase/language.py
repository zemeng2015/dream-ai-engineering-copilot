# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

LANGUAGE_BY_EXTENSION = {
    ".java": "java",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".properties": "properties",
    ".env": "env",
}

CONFIG_EXTENSIONS = {".yaml", ".yml", ".json", ".properties", ".env", ".toml"}


def detect_language(path: Path) -> str:
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "unknown")


def classify_role(relative_path: str, language: str) -> str:
    normalized = relative_path.replace("\\", "/").lower()
    name = Path(normalized).name
    suffix = Path(normalized).suffix
    if language == "markdown" or "/docs/" in normalized:
        return "docs"
    if suffix in CONFIG_EXTENSIONS or name in {"dockerfile", "makefile"}:
        return "config"
    if (
        "/test/" in normalized
        or "/tests/" in normalized
        or name.startswith("test_")
        or name.endswith("test.java")
        or name.endswith(".spec.ts")
        or name.endswith(".test.ts")
    ):
        return "test"
    if language in {"java", "python", "typescript", "javascript"}:
        return "source"
    return "unknown"
