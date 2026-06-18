from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from dq_monitoring.generator import GeneratedBatch

CRITICAL_COLUMNS = ("external_record_id", "event_ts", "customer_id")
MEASURED_COLUMNS = (*CRITICAL_COLUMNS, "amount", "status")
MISSING_FRESHNESS_LAG_MINUTES = 99999.0


@dataclass(frozen=True)
class QualityMetrics:
    source_id: int
    batch_date: object
    completeness_rate: float
    freshness_lag_minutes: float
    duplicate_rate: float
    null_rate: float
    record_count_delta: float
    schema_drift_flag: bool
    failed_jobs_count: int
    total_records: int

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([self.__dict__])


def calculate_metrics(
    source: pd.Series,
    batch_date: object,
    batch: GeneratedBatch,
) -> QualityMetrics:
    records = batch.records
    total_records = len(records)

    if total_records == 0:
        completeness_rate = 0.0
        null_rate = 1.0
        duplicate_rate = 0.0
        freshness_lag_minutes = MISSING_FRESHNESS_LAG_MINUTES
    else:
        completeness_rate = _completeness_rate(records, total_records)
        null_rate = _null_rate(records, total_records)
        duplicate_rate = _duplicate_rate(records, total_records)
        freshness_lag_minutes = _freshness_lag_minutes(records, batch.received_at)

    expected_records = int(source.expected_daily_records)
    if expected_records <= 0:
        raise ValueError("expected_daily_records must be greater than 0")
    record_count_delta = (total_records - expected_records) / expected_records

    return QualityMetrics(
        source_id=int(source.source_id),
        batch_date=batch_date,
        completeness_rate=round(max(0.0, min(1.0, completeness_rate)), 4),
        freshness_lag_minutes=round(float(freshness_lag_minutes), 2),
        duplicate_rate=round(max(0.0, duplicate_rate), 4),
        null_rate=round(max(0.0, null_rate), 4),
        record_count_delta=round(float(record_count_delta), 4),
        schema_drift_flag=batch.schema_hash != batch.expected_schema_hash,
        failed_jobs_count=1 if batch.job_status == "failed" else 0,
        total_records=total_records,
    )


def _completeness_rate(records: pd.DataFrame, total_records: int) -> float:
    observed_cells = total_records * len(CRITICAL_COLUMNS)
    missing_critical = int(records[list(CRITICAL_COLUMNS)].isna().sum().sum())
    return 1.0 - (missing_critical / observed_cells)


def _null_rate(records: pd.DataFrame, total_records: int) -> float:
    measured_cells = total_records * len(MEASURED_COLUMNS)
    missing_measured = int(records[list(MEASURED_COLUMNS)].isna().sum().sum())
    return missing_measured / measured_cells


def _duplicate_rate(records: pd.DataFrame, total_records: int) -> float:
    external_ids = records["external_record_id"].dropna()
    if external_ids.empty:
        return 0.0

    return float(external_ids.duplicated().sum() / total_records)


def _freshness_lag_minutes(records: pd.DataFrame, received_at: datetime) -> float:
    event_ts = pd.to_datetime(records["event_ts"], utc=True, errors="coerce").dropna()
    if event_ts.empty:
        return MISSING_FRESHNESS_LAG_MINUTES

    max_event_ts: datetime = event_ts.max().to_pydatetime()
    return max(0.0, (received_at - max_event_ts).total_seconds() / 60)
