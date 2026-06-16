# Data Quality Monitoring System

[![CI](https://github.com/minkinad/data-quality-monitoring-system/actions/workflows/ci.yml/badge.svg)](https://github.com/minkinad/data-quality-monitoring-system/actions/workflows/ci.yml)
[![CD](https://github.com/minkinad/data-quality-monitoring-system/actions/workflows/cd.yml/badge.svg)](https://github.com/minkinad/data-quality-monitoring-system/actions/workflows/cd.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Production-style demo project for monitoring quality of data received from external sources.

The system simulates daily ingestion from multiple sources, validates batches, calculates data quality metrics, creates incidents when thresholds are breached, and exposes a Streamlit dashboard plus Grafana provisioning.

## What This Project Shows

- External data sources with separate owners, domains, SLAs, and schemas.
- Daily incoming batches with realistic defects: missing values, duplicates, stale loads, schema drift, anomalous volumes, and failed jobs.
- Quality metrics:
  - `completeness_rate`
  - `freshness_lag_minutes`
  - `duplicate_rate`
  - `null_rate`
  - `record_count_delta`
  - `schema_drift_flag`
  - `failed_jobs_count`
- Incident creation based on configurable thresholds.
- Source status table for operational monitoring.
- Streamlit dashboard for analysts and data operations.
- PostgreSQL SQL layer with analytical views.
- Grafana dashboard provisioning for operational observability.

## Architecture

```text
external source simulator
        |
        v
raw_batches / raw_records  ---- pandera validation
        |
        v
dq_metrics  ---- threshold evaluation ---- dq_incidents
        |
        v
SQL views: source status, daily quality, incident summary
        |
        +---- Streamlit dashboard
        +---- Grafana dashboard
```

## Repository Structure

```text
.
├── app/
│   └── dashboard.py
├── docker-compose.yml
├── grafana/
│   └── provisioning/
├── scripts/
│   └── run_pipeline.py
├── sql/
│   ├── 001_schema.sql
│   ├── 002_views.sql
│   └── 003_seed_sources.sql
├── src/
│   └── dq_monitoring/
├── tests/
├── .env.example
└── pyproject.toml
```

## Quick Start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Start PostgreSQL and Grafana:

```bash
docker compose up -d postgres grafana
```

3. Install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

4. Run the demo pipeline for 30 days of source batches:

```bash
python scripts/run_pipeline.py --days 30 --reset
```

5. Start the Streamlit dashboard:

```bash
streamlit run app/dashboard.py
```

Services:

- Streamlit: http://localhost:8501
- Grafana: http://localhost:3000
- PostgreSQL: `localhost:5432`

Default Grafana credentials are `admin` / `admin`.

## CI/CD

GitHub Actions workflows live in `.github/workflows`.

- `CI`: runs on pull requests and pushes to `main`; checks Ruff linting, unit tests, Grafana JSON validity, Docker Compose config, and a PostgreSQL smoke test.
- `CD`: runs after a successful `CI` workflow on `main` and on manual dispatch; builds the Streamlit Docker image and publishes it to GitHub Container Registry.

Published image:

```text
ghcr.io/<owner>/data-quality-monitoring-system:<git-sha>
ghcr.io/<owner>/data-quality-monitoring-system:latest
```

Local Docker build:

```bash
docker compose build dashboard
docker compose up -d postgres dashboard grafana
```

## Analyst Workflow

The project is designed around practical Technical Data Analyst work:

1. Check the source status table.
2. Find sources with degraded health.
3. Drill into metric trends by source.
4. Review open incidents and breach reasons.
5. Use SQL views for ad hoc investigation.

Useful SQL:

```sql
select * from mart_source_status order by status, source_name;
select * from mart_daily_quality where metric_date >= current_date - interval '7 days';
select * from mart_incident_summary order by opened_at desc;
```

## Configuration

Thresholds live in `config/thresholds.yml`.

Source metadata is seeded from `sql/003_seed_sources.sql`.

Main environment variables:

```text
DATABASE_URL=postgresql+psycopg://dq_user:dq_password@localhost:5432/dq_monitoring
DQ_ENV=local
```

## Data Model

Core tables:

- `data_sources`: metadata and SLA for each external source.
- `ingestion_jobs`: one load attempt per source and date.
- `raw_batches`: batch-level payload metadata.
- `raw_records`: generated source records.
- `dq_metrics`: daily quality metrics per source.
- `dq_incidents`: threshold breaches and operational incidents.

## Tests

```bash
pytest
```

The tests focus on metric calculation and incident classification logic.
