# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dream.core.paths import ensure_artifacts_dir  # noqa: E402
from dream.leadership_demo.preflight import LeadershipPreflightRunner  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset, validate, and report the provider-neutral leadership demo gate."
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--strict-git",
        action="store_true",
        help="Fail when the working tree is not clean.",
    )
    parser.add_argument(
        "--require-frontend-bundle",
        action="store_true",
        help="Fail instead of warn when the Angular production bundle is missing.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ensure_artifacts_dir() / "leadership-preflight",
    )
    args = parser.parse_args()
    report = LeadershipPreflightRunner().run(
        output_dir=args.output_dir,
        repetitions=args.repetitions,
        strict_git=args.strict_git,
        require_frontend_bundle=args.require_frontend_bundle,
    )
    print(report.model_dump_json(indent=2))
    if not report.ready_for_demo:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
