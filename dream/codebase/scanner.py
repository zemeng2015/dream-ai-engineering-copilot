# SPDX-License-Identifier: Apache-2.0

import hashlib
from pathlib import Path

from dream.codebase.language import classify_role, detect_language
from dream.codebase.models import FileNode
from dream.core.paths import display_path, resolve_project_path
from dream.security.models import ResourceAccess

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "node_modules",
    "target",
    "build",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
}


class CodebaseScanner:
    def scan(
        self,
        repo_path: str | Path,
        *,
        access: ResourceAccess | None = None,
    ) -> list[FileNode]:
        root = resolve_project_path(repo_path, must_exist=True)
        repo_access = access or ResourceAccess()
        files: list[FileNode] = []
        for path in sorted(self._walk_files(root)):
            relative_path = path.relative_to(root).as_posix()
            language = detect_language(path)
            text = self._read_text(path)
            line_count = len(text.splitlines()) if text is not None else 0
            files.append(
                FileNode(
                    file_id=self._stable_id(f"{display_path(root)}:{relative_path}"),
                    path=relative_path,
                    language=language,
                    size_bytes=path.stat().st_size,
                    line_count=line_count,
                    role=classify_role(relative_path, language),
                    access=repo_access.model_copy(deep=True),
                )
            )
        return files

    def _walk_files(self, root: Path) -> list[Path]:
        discovered: list[Path] = []
        stack = [root]
        while stack:
            current = stack.pop()
            for child in current.iterdir():
                if child.is_dir():
                    if child.name not in IGNORED_DIRECTORIES:
                        stack.append(child)
                elif child.is_file():
                    discovered.append(child)
        return discovered

    @staticmethod
    def _read_text(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
