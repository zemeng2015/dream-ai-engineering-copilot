# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dream.leadership_demo import LeadershipDemoService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the deterministic provider-neutral DREAM leadership scenario."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Replace the existing fixed leadership case and its case-scoped audit/eval rows.",
    )
    args = parser.parse_args()
    result = LeadershipDemoService().seed(reset=args.reset)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
