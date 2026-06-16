create or replace view mart_source_status as
with latest_metric as (
    select distinct on (m.source_id)
        m.*
    from dq_metrics m
    order by m.source_id, m.batch_date desc, m.calculated_at desc
),
open_incidents as (
    select
        source_id,
        count(*) as open_incidents,
        count(*) filter (where severity = 'critical') as critical_incidents
    from dq_incidents
    where status in ('open', 'acknowledged')
    group by source_id
)
select
    s.source_id,
    s.source_name,
    s.domain,
    s.owner_team,
    lm.batch_date as last_batch_date,
    case
        when lm.source_id is null then 'no_data'
        when coalesce(oi.critical_incidents, 0) > 0 then 'critical'
        when coalesce(oi.open_incidents, 0) > 0 then 'warning'
        when lm.schema_drift_flag then 'warning'
        else 'healthy'
    end as status,
    lm.completeness_rate,
    lm.freshness_lag_minutes,
    lm.duplicate_rate,
    lm.null_rate,
    lm.record_count_delta,
    lm.schema_drift_flag,
    lm.failed_jobs_count,
    coalesce(oi.open_incidents, 0) as open_incidents
from data_sources s
left join latest_metric lm on lm.source_id = s.source_id
left join open_incidents oi on oi.source_id = s.source_id
where s.is_active;

create or replace view mart_daily_quality as
select
    m.batch_date as metric_date,
    s.source_name,
    s.domain,
    s.owner_team,
    m.completeness_rate,
    m.freshness_lag_minutes,
    m.duplicate_rate,
    m.null_rate,
    m.record_count_delta,
    m.schema_drift_flag,
    m.failed_jobs_count,
    m.total_records,
    m.calculated_at
from dq_metrics m
join data_sources s on s.source_id = m.source_id;

create or replace view mart_incident_summary as
select
    i.incident_id,
    i.batch_date,
    s.source_name,
    s.domain,
    s.owner_team,
    i.metric_name,
    i.metric_value,
    i.threshold_value,
    i.severity,
    i.status,
    i.title,
    i.details,
    i.opened_at,
    i.resolved_at
from dq_incidents i
join data_sources s on s.source_id = i.source_id;
