# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.core.errors import NotFoundError, PathTraversalError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_PACKS_DIR = PROJECT_ROOT / "knowledge_packs"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DEFAULT_DB_PATH = PROJECT_ROOT / "dream.sqlite"


def ensure_artifacts_dir() -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR


def resolve_project_path(path_value: str | Path, *, must_exist: bool = False) -> Path:
    raw_path = Path(path_value)
    candidate = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(PROJECT_ROOT):
        raise PathTraversalError(f"Path escapes project root: {path_value}")
    if must_exist and not resolved.exists():
        raise NotFoundError(f"Path does not exist: {path_value}")
    return resolved


def display_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()

