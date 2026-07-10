# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dream.core.paths import ensure_artifacts_dir  # noqa: E402
from dream.leadership_demo.release import LeadershipReleaseBuilder  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a checksummed DREAM leadership presentation release manifest."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require clean Git state and clean-git preflight before marking frozen.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ensure_artifacts_dir() / "leadership-release",
    )
    args = parser.parse_args()
    manifest = LeadershipReleaseBuilder().build(
        output_dir=args.output_dir,
        strict=args.strict,
    )
    print(manifest.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
