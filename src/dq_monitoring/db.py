from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from dq_monitoring.config import PROJECT_ROOT, get_settings


def get_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or get_settings().database_url, pool_pre_ping=True)


def run_sql_file(engine: Engine, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))


def reset_database(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("drop view if exists mart_incident_summary cascade"))
        conn.execute(text("drop view if exists mart_daily_quality cascade"))
        conn.execute(text("drop view if exists mart_source_status cascade"))
        conn.execute(text("drop table if exists dq_incidents cascade"))
        conn.execute(text("drop table if exists dq_metrics cascade"))
        conn.execute(text("drop table if exists raw_records cascade"))
        conn.execute(text("drop table if exists raw_batches cascade"))
        conn.execute(text("drop table if exists ingestion_jobs cascade"))
        conn.execute(text("drop table if exists data_sources cascade"))

    for file_name in ("001_schema.sql", "002_views.sql", "003_seed_sources.sql"):
        run_sql_file(engine, PROJECT_ROOT / "sql" / file_name)


def fetch_sources(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        select
            source_id,
            source_name,
            source_type,
            domain,
            owner_team,
            expected_daily_records,
            freshness_sla_minutes
        from data_sources
        where is_active
        order by source_id
        """,
        engine,
    )


def fetch_dataframe(engine: Engine, query: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql(text(query), engine, params=params)


def insert_dataframe(
    engine: Engine,
    table_name: str,
    rows: pd.DataFrame,
    *,
    if_exists: str = "append",
    dtype: dict | None = None,
) -> None:
    if rows.empty:
        return
    rows.to_sql(
        table_name,
        engine,
        if_exists=if_exists,
        index=False,
        method="multi",
        chunksize=1000,
        dtype=dtype,
    )


def execute_scalar(engine: Engine, statement: str, params: dict | None = None) -> int:
    with engine.begin() as conn:
        return int(conn.execute(text(statement), params or {}).scalar_one())


def execute_many(engine: Engine, statements: Iterable[tuple[str, dict]]) -> None:
    with engine.begin() as conn:
        for statement, params in statements:
            conn.execute(text(statement), params)
