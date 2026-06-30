# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from dream.core.errors import NotFoundError, PathTraversalError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_PACKS_DIR = PROJECT_ROOT / "knowledge_packs"
DEFAULT_ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DEFAULT_DB_PATH = PROJECT_ROOT / "dream.sqlite"
KNOWLEDGE_PACKS_DIR = DEFAULT_KNOWLEDGE_PACKS_DIR
ARTIFACTS_DIR = DEFAULT_ARTIFACTS_DIR


def get_knowledge_packs_dir() -> Path:
    from dream.config.loader import resolve_config

    return resolve_config().knowledge.root


def ensure_artifacts_dir() -> Path:
    artifacts_dir = get_artifacts_dir()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


def get_artifacts_dir() -> Path:
    from dream.config.loader import resolve_config

    return resolve_config().artifacts.root


def get_audit_db_path() -> Path:
    from dream.config.loader import resolve_config

    return resolve_config().audit.sqlite_path


def resolve_artifact_path(relative_path: str | Path) -> Path:
    artifacts_dir = ensure_artifacts_dir().resolve()
    raw_path = Path(relative_path)
    candidate = raw_path if raw_path.is_absolute() else artifacts_dir / raw_path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(artifacts_dir):
        raise PathTraversalError(f"Artifact path escapes artifact root: {relative_path}")
    return resolved


def resolve_project_path(path_value: str | Path, *, must_exist: bool = False) -> Path:
    raw_path = Path(path_value)
    candidate = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
    resolved = candidate.resolve()
    allowed_roots = [PROJECT_ROOT.resolve(), get_artifacts_dir().resolve()]
    if not any(resolved.is_relative_to(root) for root in allowed_roots):
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
