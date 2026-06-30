# SPDX-License-Identifier: Apache-2.0

import pytest

from dream.core.errors import PathTraversalError
from dream.extensions import LocalArtifactStore


def test_local_artifact_store_contract(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")

    written = store.write_text("nested/output.md", "# Output\n")

    assert written.is_relative_to(store.root)
    assert store.read_text("nested/output.md") == "# Output\n"


def test_local_artifact_store_contract_prevents_traversal(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")

    with pytest.raises(PathTraversalError):
        store.resolve_path("../outside.md")
