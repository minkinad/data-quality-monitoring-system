from __future__ import annotations

import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema


RAW_RECORD_SCHEMA = DataFrameSchema(
    {
        "external_record_id": Column(str, nullable=True),
        "event_ts": Column(pa.DateTime, nullable=True),
        "customer_id": Column(str, nullable=True),
        "amount": Column(float, nullable=True, coerce=True),
        "status": Column(str, nullable=True),
        "payload": Column(object, nullable=False),
    },
    strict=True,
    coerce=True,
)


def validate_raw_records(records: pd.DataFrame) -> pd.DataFrame:
    return RAW_RECORD_SCHEMA.validate(records, lazy=True)
