from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

import pandas as pd
from sqlalchemy import Engine, text
from sqlalchemy.dialects.postgresql import JSONB

from dq_monitoring.config import load_thresholds
from dq_monitoring.db import fetch_sources, insert_dataframe
from dq_monitoring.generator import generate_batch
from dq_monitoring.incidents import build_incidents
from dq_monitoring.metrics import calculate_metrics
from dq_monitoring.validation import validate_raw_records


def run_pipeline(engine: Engine, *, start_date: date, days: int) -> dict[str, int]:
    thresholds = load_thresholds()
    sources = fetch_sources(engine)
    if sources.empty:
        raise RuntimeError("No active sources found. Run SQL seed script first.")

    stats = {"jobs": 0, "records": 0, "metrics": 0, "incidents": 0}
    for offset in range(days):
        batch_date = start_date + timedelta(days=offset)
        for _, source in sources.iterrows():
            batch = generate_batch(source, batch_date)
            validated_records = validate_raw_records(batch.records)

            job_id = _upsert_job(engine, source, batch_date, batch)
            batch_id = _insert_batch(engine, source, batch_date, job_id, batch)
            _insert_records(engine, source, batch_id, validated_records)

            metrics = calculate_metrics(source, batch_date, batch)
            _upsert_metrics(engine, metrics.to_frame())

            incidents = build_incidents(source, metrics, thresholds)
            _upsert_incidents(engine, incidents)

            stats["jobs"] += 1
            stats["records"] += len(validated_records)
            stats["metrics"] += 1
            stats["incidents"] += len(incidents)

    return stats


def _upsert_job(engine: Engine, source: pd.Series, batch_date: date, batch) -> int:
    started_at = datetime.combine(batch_date + timedelta(days=1), time(hour=6), tzinfo=UTC)
    with engine.begin() as conn:
        return int(
            conn.execute(
                text(
                    """
                    insert into ingestion_jobs (
                        source_id,
                        batch_date,
                        started_at,
                        finished_at,
                        status,
                        error_message,
                        inserted_records
                    )
                    values (
                        :source_id,
                        :batch_date,
                        :started_at,
                        :finished_at,
                        :status,
                        :error_message,
                        :inserted_records
                    )
                    on conflict (source_id, batch_date) do update set
                        started_at = excluded.started_at,
                        finished_at = excluded.finished_at,
                        status = excluded.status,
                        error_message = excluded.error_message,
                        inserted_records = excluded.inserted_records
                    returning job_id
                    """
                ),
                {
                    "source_id": int(source.source_id),
                    "batch_date": batch_date,
                    "started_at": started_at,
                    "finished_at": batch.received_at,
                    "status": batch.job_status,
                    "error_message": batch.error_message,
                    "inserted_records": len(batch.records),
                },
            ).scalar_one()
        )


def _insert_batch(engine: Engine, source: pd.Series, batch_date: date, job_id: int, batch) -> int:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                delete from raw_batches
                where source_id = :source_id and batch_date = :batch_date
                """
            ),
            {"source_id": int(source.source_id), "batch_date": batch_date},
        )
        return int(
            conn.execute(
                text(
                    """
                    insert into raw_batches (
                        job_id,
                        source_id,
                        batch_date,
                        received_at,
                        schema_version,
                        schema_hash,
                        expected_schema_hash,
                        row_count
                    )
                    values (
                        :job_id,
                        :source_id,
                        :batch_date,
                        :received_at,
                        :schema_version,
                        :schema_hash,
                        :expected_schema_hash,
                        :row_count
                    )
                    returning batch_id
                    """
                ),
                {
                    "job_id": job_id,
                    "source_id": int(source.source_id),
                    "batch_date": batch_date,
                    "received_at": batch.received_at,
                    "schema_version": batch.schema_version,
                    "schema_hash": batch.schema_hash,
                    "expected_schema_hash": batch.expected_schema_hash,
                    "row_count": len(batch.records),
                },
            ).scalar_one()
        )


def _insert_records(
    engine: Engine,
    source: pd.Series,
    batch_id: int,
    records: pd.DataFrame,
) -> None:
    rows = records.copy()
    rows.insert(0, "source_id", int(source.source_id))
    rows.insert(0, "batch_id", batch_id)
    insert_dataframe(engine, "raw_records", rows, dtype={"payload": JSONB})


def _upsert_metrics(engine: Engine, metrics: pd.DataFrame) -> None:
    rows = metrics.to_dict(orient="records")
    with engine.begin() as conn:
        for row in rows:
            conn.execute(
                text(
                    """
                    insert into dq_metrics (
                        source_id,
                        batch_date,
                        completeness_rate,
                        freshness_lag_minutes,
                        duplicate_rate,
                        null_rate,
                        record_count_delta,
                        schema_drift_flag,
                        failed_jobs_count,
                        total_records
                    )
                    values (
                        :source_id,
                        :batch_date,
                        :completeness_rate,
                        :freshness_lag_minutes,
                        :duplicate_rate,
                        :null_rate,
                        :record_count_delta,
                        :schema_drift_flag,
                        :failed_jobs_count,
                        :total_records
                    )
                    on conflict (source_id, batch_date) do update set
                        completeness_rate = excluded.completeness_rate,
                        freshness_lag_minutes = excluded.freshness_lag_minutes,
                        duplicate_rate = excluded.duplicate_rate,
                        null_rate = excluded.null_rate,
                        record_count_delta = excluded.record_count_delta,
                        schema_drift_flag = excluded.schema_drift_flag,
                        failed_jobs_count = excluded.failed_jobs_count,
                        total_records = excluded.total_records,
                        calculated_at = now()
                    """
                ),
                row,
            )


def _upsert_incidents(engine: Engine, incidents: pd.DataFrame) -> None:
    if incidents.empty:
        return
    rows = incidents.to_dict(orient="records")
    with engine.begin() as conn:
        for row in rows:
            conn.execute(
                text(
                    """
                    insert into dq_incidents (
                        source_id,
                        batch_date,
                        metric_name,
                        metric_value,
                        threshold_value,
                        severity,
                        status,
                        title,
                        details
                    )
                    values (
                        :source_id,
                        :batch_date,
                        :metric_name,
                        :metric_value,
                        :threshold_value,
                        :severity,
                        :status,
                        :title,
                        :details
                    )
                    on conflict (source_id, batch_date, metric_name) do update set
                        metric_value = excluded.metric_value,
                        threshold_value = excluded.threshold_value,
                        severity = excluded.severity,
                        status = case
                            when dq_incidents.status = 'resolved' then 'open'
                            else dq_incidents.status
                        end,
                        title = excluded.title,
                        details = excluded.details
                    """
                ),
                row,
            )
