from __future__ import annotations

import textwrap

import pytest

from dq_monitoring.config import load_thresholds


def test_load_thresholds_returns_valid_config() -> None:
    thresholds = load_thresholds()

    assert thresholds["severity"]["warning"]["completeness_rate_min"] == 0.95
    assert thresholds["global"]["failed_jobs_count_max"] == 0


def test_load_thresholds_rejects_missing_required_keys(tmp_path) -> None:
    config_path = tmp_path / "thresholds.yml"
    config_path.write_text(
        textwrap.dedent(
            """
            global:
              completeness_rate_min: 0.95
            severity:
              warning:
                completeness_rate_min: 0.95
              critical:
                completeness_rate_min: 0.85
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing keys"):
        load_thresholds(config_path)


def test_load_thresholds_rejects_invalid_severity_ordering(tmp_path) -> None:
    config_path = tmp_path / "thresholds.yml"
    config_path.write_text(
        textwrap.dedent(
            """
            global:
              completeness_rate_min: 0.95
              freshness_lag_minutes_max: 180
              duplicate_rate_max: 0.02
              null_rate_max: 0.03
              record_count_delta_abs_max: 0.35
              failed_jobs_count_max: 0
            severity:
              warning:
                completeness_rate_min: 0.95
                freshness_lag_minutes_max: 180
                duplicate_rate_max: 0.02
                null_rate_max: 0.03
                record_count_delta_abs_max: 0.35
              critical:
                completeness_rate_min: 0.99
                freshness_lag_minutes_max: 720
                duplicate_rate_max: 0.10
                null_rate_max: 0.15
                record_count_delta_abs_max: 0.70
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="completeness_rate_min"):
        load_thresholds(config_path)
