# Analyst Playbook

## Daily Monitoring

Start with `mart_source_status`.

```sql
select *
from mart_source_status
order by status, open_incidents desc, source_name;
```

Prioritize sources in this order:

1. `critical`
2. `warning`
3. `no_data`
4. `healthy`

## Investigation Queries

Check the latest metric trend for a source:

```sql
select *
from mart_daily_quality
where source_name = 'payments_gateway_sftp'
order by metric_date desc
limit 14;
```

Find current open incidents:

```sql
select *
from mart_incident_summary
where status in ('open', 'acknowledged')
order by severity, opened_at desc;
```

Inspect raw batch metadata:

```sql
select
    s.source_name,
    b.batch_date,
    b.received_at,
    b.schema_version,
    b.schema_hash <> b.expected_schema_hash as schema_drift,
    b.row_count,
    j.status as job_status,
    j.error_message
from raw_batches b
join data_sources s on s.source_id = b.source_id
join ingestion_jobs j on j.job_id = b.job_id
order by b.batch_date desc, s.source_name;
```

## Metric Interpretation

| Metric | Meaning | Typical action |
| --- | --- | --- |
| `completeness_rate` | Share of populated critical fields. | Check upstream mapping and required fields. |
| `freshness_lag_minutes` | Delay between latest event time and batch receipt. | Check source delivery, API delay, or scheduler. |
| `duplicate_rate` | Share of duplicated external record IDs. | Check incremental extraction keys. |
| `null_rate` | Null share across measured fields. | Check schema mapping and source contract. |
| `record_count_delta` | Difference from expected daily volume. | Compare to business calendar and upstream job logs. |
| `schema_drift_flag` | Payload differs from expected schema contract. | Confirm upstream release or contract change. |
| `failed_jobs_count` | Failed ingestion attempts for the batch. | Escalate to data engineering or source owner. |
