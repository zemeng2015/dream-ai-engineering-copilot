# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dream.core.paths import ensure_artifacts_dir  # noqa: E402
from dream.leadership_demo.release import LeadershipReleaseVerifier  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify source, evidence, and frontend hashes in a leadership release."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=(
            ensure_artifacts_dir()
            / "leadership-release/leadership-release-manifest.json"
        ),
    )
    args = parser.parse_args()
    report = LeadershipReleaseVerifier().verify(args.manifest)
    print(report.model_dump_json(indent=2))
    if not report.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
