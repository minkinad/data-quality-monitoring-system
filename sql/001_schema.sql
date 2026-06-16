create table if not exists data_sources (
    source_id serial primary key,
    source_name text not null unique,
    source_type text not null,
    domain text not null,
    owner_team text not null,
    expected_daily_records integer not null check (expected_daily_records > 0),
    freshness_sla_minutes integer not null check (freshness_sla_minutes > 0),
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists ingestion_jobs (
    job_id bigserial primary key,
    source_id integer not null references data_sources(source_id),
    batch_date date not null,
    started_at timestamptz not null,
    finished_at timestamptz,
    status text not null check (status in ('success', 'failed')),
    error_message text,
    inserted_records integer not null default 0,
    unique (source_id, batch_date)
);

create table if not exists raw_batches (
    batch_id bigserial primary key,
    job_id bigint not null references ingestion_jobs(job_id) on delete cascade,
    source_id integer not null references data_sources(source_id),
    batch_date date not null,
    received_at timestamptz not null,
    schema_version text not null,
    schema_hash text not null,
    expected_schema_hash text not null,
    row_count integer not null check (row_count >= 0),
    created_at timestamptz not null default now()
);

create table if not exists raw_records (
    record_pk bigserial primary key,
    batch_id bigint not null references raw_batches(batch_id) on delete cascade,
    source_id integer not null references data_sources(source_id),
    external_record_id text,
    event_ts timestamptz,
    customer_id text,
    amount numeric(12, 2),
    status text,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists dq_metrics (
    metric_id bigserial primary key,
    source_id integer not null references data_sources(source_id),
    batch_date date not null,
    completeness_rate numeric(7, 4) not null,
    freshness_lag_minutes numeric(12, 2) not null,
    duplicate_rate numeric(7, 4) not null,
    null_rate numeric(7, 4) not null,
    record_count_delta numeric(9, 4) not null,
    schema_drift_flag boolean not null,
    failed_jobs_count integer not null,
    total_records integer not null,
    calculated_at timestamptz not null default now(),
    unique (source_id, batch_date)
);

create table if not exists dq_incidents (
    incident_id bigserial primary key,
    source_id integer not null references data_sources(source_id),
    batch_date date not null,
    metric_name text not null,
    metric_value numeric(12, 4),
    threshold_value numeric(12, 4),
    severity text not null check (severity in ('warning', 'critical')),
    status text not null check (status in ('open', 'acknowledged', 'resolved')) default 'open',
    title text not null,
    details text not null,
    opened_at timestamptz not null default now(),
    resolved_at timestamptz,
    unique (source_id, batch_date, metric_name)
);

create index if not exists idx_ingestion_jobs_source_date on ingestion_jobs(source_id, batch_date);
create index if not exists idx_raw_records_batch on raw_records(batch_id);
create index if not exists idx_dq_metrics_source_date on dq_metrics(source_id, batch_date);
create index if not exists idx_dq_incidents_status on dq_incidents(status, severity);
