from __future__ import annotations

from datetime import date

import pandas as pd

from dq_monitoring.config import load_thresholds
from dq_monitoring.incidents import build_incidents
from dq_monitoring.metrics import QualityMetrics


def test_build_incidents_classifies_metric_breaches() -> None:
    source = pd.Series({"source_id": 1, "source_name": "payments_gateway_sftp"})
    metrics = QualityMetrics(
        source_id=1,
        batch_date=date(2026, 1, 1),
        completeness_rate=0.80,
        freshness_lag_minutes=900.0,
        duplicate_rate=0.12,
        null_rate=0.20,
        record_count_delta=-0.75,
        schema_drift_flag=True,
        failed_jobs_count=1,
        total_records=100,
    )

    incidents = build_incidents(source, metrics, load_thresholds())

    assert set(incidents["metric_name"]) == {
        "completeness_rate",
        "freshness_lag_minutes",
        "duplicate_rate",
        "null_rate",
        "record_count_delta",
        "schema_drift_flag",
        "failed_jobs_count",
    }
    assert "critical" in set(incidents["severity"])
