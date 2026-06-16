from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from dq_monitoring.generator import GeneratedBatch


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


def calculate_metrics(source: pd.Series, batch_date: object, batch: GeneratedBatch) -> QualityMetrics:
    records = batch.records
    total_records = len(records)

    if total_records == 0:
        completeness_rate = 0.0
        null_rate = 1.0
        duplicate_rate = 0.0
        freshness_lag_minutes = 99999.0
    else:
        critical_columns = ["external_record_id", "event_ts", "customer_id"]
        observed_cells = total_records * len(critical_columns)
        missing_critical = int(records[critical_columns].isna().sum().sum())
        completeness_rate = 1.0 - (missing_critical / observed_cells)

        measured_columns = ["external_record_id", "event_ts", "customer_id", "amount", "status"]
        null_rate = float(records[measured_columns].isna().sum().sum() / (total_records * len(measured_columns)))

        duplicate_rate = float(records["external_record_id"].duplicated().sum() / total_records)

        event_ts = pd.to_datetime(records["event_ts"], utc=True, errors="coerce").dropna()
        if event_ts.empty:
            freshness_lag_minutes = 99999.0
        else:
            max_event_ts: datetime = event_ts.max().to_pydatetime()
            freshness_lag_minutes = (batch.received_at - max_event_ts).total_seconds() / 60

    expected_records = int(source.expected_daily_records)
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
