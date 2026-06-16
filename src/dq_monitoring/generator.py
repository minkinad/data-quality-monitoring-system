from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd


EXPECTED_SCHEMA_HASH = "external_record_id|event_ts|customer_id|amount|status|payload:v1"


@dataclass(frozen=True)
class GeneratedBatch:
    records: pd.DataFrame
    received_at: datetime
    schema_version: str
    schema_hash: str
    expected_schema_hash: str
    job_status: str
    error_message: str | None


def stable_seed(*parts: Any) -> int:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def _defect_profile(source_name: str, batch_date: date) -> dict[str, bool]:
    seed = stable_seed(source_name, batch_date.isoformat())
    return {
        "failed_job": seed % 31 == 0,
        "schema_drift": seed % 17 == 0,
        "late_delivery": seed % 13 == 0,
        "duplicate_spike": seed % 11 == 0,
        "null_spike": seed % 7 == 0,
        "volume_drop": seed % 19 == 0,
        "volume_spike": seed % 23 == 0,
    }


def generate_batch(source: pd.Series, batch_date: date) -> GeneratedBatch:
    profile = _defect_profile(str(source.source_name), batch_date)
    rng = np.random.default_rng(stable_seed(source.source_name, batch_date.isoformat(), "records"))

    expected_records = int(source.expected_daily_records)
    if profile["volume_drop"]:
        row_count = int(expected_records * rng.uniform(0.35, 0.62))
    elif profile["volume_spike"]:
        row_count = int(expected_records * rng.uniform(1.55, 1.95))
    else:
        row_count = int(expected_records * rng.uniform(0.92, 1.08))

    if profile["failed_job"]:
        row_count = int(row_count * 0.1)

    base_event_time = datetime.combine(batch_date, time(hour=20), tzinfo=timezone.utc)
    event_offsets = rng.integers(0, 16 * 60, size=row_count)
    event_ts = [base_event_time - timedelta(minutes=int(offset)) for offset in event_offsets]

    source_prefix = str(source.source_name).split("_")[0]
    external_ids = [f"{source_prefix}-{batch_date:%Y%m%d}-{idx:06d}" for idx in range(row_count)]

    duplicate_share = 0.08 if profile["duplicate_spike"] else 0.006
    duplicate_count = int(row_count * duplicate_share)
    for idx in range(duplicate_count):
        if row_count > 1:
            external_ids[-idx - 1] = external_ids[idx]

    customer_ids = [f"cust-{rng.integers(10000, 99999)}" for _ in range(row_count)]
    amount = np.round(rng.gamma(shape=2.2, scale=45.0, size=row_count), 2)
    statuses = rng.choice(["new", "processed", "cancelled", "refunded"], size=row_count, p=[0.2, 0.65, 0.1, 0.05])

    null_probability = 0.11 if profile["null_spike"] else 0.012
    records = pd.DataFrame(
        {
            "external_record_id": external_ids,
            "event_ts": event_ts,
            "customer_id": customer_ids,
            "amount": amount,
            "status": statuses,
        }
    )

    nullable_columns = ["external_record_id", "event_ts", "customer_id", "amount", "status"]
    for column in nullable_columns:
        mask = rng.random(row_count) < null_probability
        records.loc[mask, column] = None

    payloads: list[dict[str, Any]] = []
    for idx in range(row_count):
        payload = {
            "source_type": source.source_type,
            "domain": source.domain,
            "row_number": idx,
        }
        if profile["schema_drift"]:
            payload["unexpected_partner_field"] = f"drift-{rng.integers(100, 999)}"
        payloads.append(payload)

    records["payload"] = payloads

    received_hour = 7
    delay_minutes = int(rng.integers(220, 900)) if profile["late_delivery"] else int(rng.integers(15, 115))
    received_at = datetime.combine(batch_date + timedelta(days=1), time(hour=received_hour), tzinfo=timezone.utc)
    received_at = received_at + timedelta(minutes=delay_minutes)

    schema_version = "v2_partner_changed" if profile["schema_drift"] else "v1"
    schema_hash = (
        EXPECTED_SCHEMA_HASH + "|unexpected_partner_field"
        if profile["schema_drift"]
        else EXPECTED_SCHEMA_HASH
    )

    return GeneratedBatch(
        records=records,
        received_at=received_at,
        schema_version=schema_version,
        schema_hash=schema_hash,
        expected_schema_hash=EXPECTED_SCHEMA_HASH,
        job_status="failed" if profile["failed_job"] else "success",
        error_message="Upstream extraction finished with partial payload" if profile["failed_job"] else None,
    )
