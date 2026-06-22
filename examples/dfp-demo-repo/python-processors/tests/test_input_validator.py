# SPDX-License-Identifier: Apache-2.0

import sys
from pathlib import Path

PROCESSOR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROCESSOR_ROOT))

from processors.input_validator import InputValidator  # noqa: E402


def test_validator_reports_missing_forecast_horizon() -> None:
    errors = InputValidator().validate_task_config(
        {"sourceDataset": "demo", "owner": "analyst"}
    )
    assert "missing required field: forecastHorizon" in errors
