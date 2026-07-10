# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dream.core.paths import ensure_artifacts_dir  # noqa: E402
from dream.leadership_demo.rehearsal import LeadershipRehearsalRunner  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rehearse blocked -> human decision -> Jira Ready, then restore the "
            "fixed blocked leadership baseline."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ensure_artifacts_dir() / "leadership-rehearsal",
    )
    args = parser.parse_args()
    report = LeadershipRehearsalRunner().run(output_dir=args.output_dir)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
