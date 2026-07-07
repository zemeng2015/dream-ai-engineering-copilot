# SPDX-License-Identifier: Apache-2.0

import json
import subprocess
import sys
from pathlib import Path


def test_raw_doc_memory_flow_acceptance_script(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_raw_doc_memory_flow.py",
            "--work-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=Path.cwd(),
        capture_output=True,
        check=False,
        text=True,
        timeout=90,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["review_event_types"] == [
        "metadata_update",
        "promotion",
        "review_decision",
    ]
    assert {
        "title",
        "target_doc_type",
        "app",
        "component",
        "concepts",
    }.issubset(payload["metadata_diff_fields"])
    assert payload["source_hash"].startswith("sha256:")
    assert payload["promoted_path"].endswith(".md")
    assert Path(payload["run_dir"]).exists()
