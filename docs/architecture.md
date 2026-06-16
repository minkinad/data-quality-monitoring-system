# Architecture

## Design Goal

The project models a practical data quality monitoring system for external data ingestion. It is intentionally small enough to run locally, but the boundaries match a production setup: ingestion metadata, raw payload storage, metric calculation, incident management, and analytical marts.

## Components

| Component | Responsibility |
| --- | --- |
| Source simulator | Creates deterministic daily batches for each external source. |
| Pandera validation | Validates raw record structure before persistence. |
| PostgreSQL raw layer | Stores job metadata, batches, and raw generated records. |
| Metric engine | Calculates quality metrics per source and date. |
| Incident engine | Converts threshold breaches into operational incidents. |
| SQL marts | Presents source status, daily quality, and incident summary views. |
| Streamlit | Analyst-facing dashboard for investigation. |
| Grafana | Operations-facing dashboard for ongoing monitoring. |

## Data Flow

1. `scripts/run_pipeline.py` loads active sources from `data_sources`.
2. The generator creates one batch per source per date.
3. Pandera validates the generated raw records.
4. The pipeline writes `ingestion_jobs`, `raw_batches`, and `raw_records`.
5. Metrics are calculated and upserted into `dq_metrics`.
6. Threshold breaches are upserted into `dq_incidents`.
7. SQL views expose monitoring-ready marts.

## Incident Strategy

Incidents are generated at the metric level. This keeps the operational surface explicit: one source can have a freshness incident, a duplicate incident, and a schema drift incident on the same batch date.

Severity is rule-based:

- `critical`: severe threshold breach or failed ingestion job.
- `warning`: moderate degradation, schema drift, or SLA risk.

## Extensibility

Production extensions would usually include:

- Airflow, Dagster, or Prefect orchestration.
- Real source connectors instead of the simulator.
- Metric history retention policies.
- Alert delivery through Slack, email, PagerDuty, or Jira.
- Source-specific thresholds and ownership routing.
- Great Expectations suites for warehouse-level assertions.
