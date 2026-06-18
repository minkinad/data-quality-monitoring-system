from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from os import getenv
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

METRIC_THRESHOLD_KEYS = {
    "completeness_rate_min",
    "freshness_lag_minutes_max",
    "duplicate_rate_max",
    "null_rate_max",
    "record_count_delta_abs_max",
}
GLOBAL_THRESHOLD_KEYS = METRIC_THRESHOLD_KEYS | {"failed_jobs_count_max"}
RATE_THRESHOLD_KEYS = {
    "completeness_rate_min",
    "duplicate_rate_max",
    "null_rate_max",
}


@dataclass(frozen=True)
class Settings:
    database_url: str
    dq_env: str = "local"


def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        database_url=getenv(
            "DATABASE_URL",
            "postgresql+psycopg://dq_user:dq_password@localhost:5432/dq_monitoring",
        ),
        dq_env=getenv("DQ_ENV", "local"),
    )


def load_thresholds(path: Path | None = None) -> dict[str, Any]:
    threshold_path = path or PROJECT_ROOT / "config" / "thresholds.yml"
    with threshold_path.open("r", encoding="utf-8") as file:
        thresholds = yaml.safe_load(file)

    _validate_thresholds(thresholds, threshold_path)
    return thresholds


def _validate_thresholds(thresholds: Any, path: Path) -> None:
    errors: list[str] = []
    if not isinstance(thresholds, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    global_thresholds = thresholds.get("global")
    severity = thresholds.get("severity")
    if not isinstance(global_thresholds, dict):
        errors.append("missing mapping: global")
        global_thresholds = {}
    if not isinstance(severity, dict):
        errors.append("missing mapping: severity")
        severity = {}

    _validate_section(
        section=global_thresholds,
        section_name="global",
        required_keys=GLOBAL_THRESHOLD_KEYS,
        errors=errors,
    )

    for level in ("warning", "critical"):
        level_thresholds = severity.get(level)
        if not isinstance(level_thresholds, dict):
            errors.append(f"missing mapping: severity.{level}")
            level_thresholds = {}
        _validate_section(
            section=level_thresholds,
            section_name=f"severity.{level}",
            required_keys=METRIC_THRESHOLD_KEYS,
            errors=errors,
        )

    if not errors:
        warning = severity["warning"]
        critical = severity["critical"]
        if float(critical["completeness_rate_min"]) > float(warning["completeness_rate_min"]):
            errors.append(
                "severity.critical.completeness_rate_min must be less than or equal to "
                "severity.warning.completeness_rate_min"
            )

        for key in METRIC_THRESHOLD_KEYS - {"completeness_rate_min"}:
            if float(critical[key]) < float(warning[key]):
                errors.append(f"severity.critical.{key} must be greater than or equal to warning")

    if errors:
        joined_errors = "; ".join(errors)
        raise ValueError(f"Invalid thresholds config at {path}: {joined_errors}")


def _validate_section(
    *,
    section: dict,
    section_name: str,
    required_keys: set[str],
    errors: list[str],
) -> None:
    missing_keys = sorted(required_keys - section.keys())
    if missing_keys:
        errors.append(f"{section_name} missing keys: {', '.join(missing_keys)}")

    for key in sorted(required_keys & section.keys()):
        value = section[key]
        if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
            errors.append(f"{section_name}.{key} must be a finite number")
            continue

        numeric_value = float(value)
        if key in RATE_THRESHOLD_KEYS and not 0 <= numeric_value <= 1:
            errors.append(f"{section_name}.{key} must be between 0 and 1")
        elif key == "freshness_lag_minutes_max" and numeric_value <= 0:
            errors.append(f"{section_name}.{key} must be greater than 0")
        elif key == "record_count_delta_abs_max" and numeric_value < 0:
            errors.append(f"{section_name}.{key} must be greater than or equal to 0")
        elif key == "failed_jobs_count_max" and numeric_value < 0:
            errors.append(f"{section_name}.{key} must be greater than or equal to 0")
