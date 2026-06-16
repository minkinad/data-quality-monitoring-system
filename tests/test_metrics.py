from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd

from dq_monitoring.generator import EXPECTED_SCHEMA_HASH, GeneratedBatch
from dq_monitoring.metrics import calculate_metrics


def test_calculate_metrics_detects_duplicates_nulls_and_schema_drift() -> None:
    source = pd.Series(
        {
            "source_id": 1,
            "source_name": "crm_accounts_api",
            "source_type": "api",
            "domain": "sales",
            "expected_daily_records": 4,
        }
    )
    records = pd.DataFrame(
        {
            "external_record_id": ["a", "a", "c", None],
            "event_ts": [
                datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
                None,
                datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
            ],
            "customer_id": ["c1", "c2", "c3", "c4"],
            "amount": [10.0, 20.0, None, 40.0],
            "status": ["new", "processed", "processed", None],
            "payload": [{}, {}, {}, {}],
        }
    )
    batch = GeneratedBatch(
        records=records,
        received_at=datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
        schema_version="v2",
        schema_hash=EXPECTED_SCHEMA_HASH + "|unexpected",
        expected_schema_hash=EXPECTED_SCHEMA_HASH,
        job_status="success",
        error_message=None,
    )

    metrics = calculate_metrics(source, date(2026, 1, 1), batch)

    assert metrics.duplicate_rate == 0.25
    assert metrics.schema_drift_flag is True
    assert metrics.failed_jobs_count == 0
    assert metrics.total_records == 4
    assert metrics.record_count_delta == 0.0
    assert metrics.freshness_lag_minutes == 60.0
    assert metrics.completeness_rate < 1.0
    assert metrics.null_rate > 0.0
