from __future__ import annotations


class InputValidator:
    required_fields = {"forecastHorizon", "sourceDataset", "owner"}

    def validate_task_config(self, config: dict[str, object]) -> list[str]:
        missing = sorted(field for field in self.required_fields if field not in config)
        errors = [f"missing required field: {field}" for field in missing]
        horizon = config.get("forecastHorizon")
        if horizon is not None and (not isinstance(horizon, int) or horizon <= 0):
            errors.append("forecastHorizon must be a positive integer")
        return errors
