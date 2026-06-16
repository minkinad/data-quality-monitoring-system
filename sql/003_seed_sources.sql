insert into data_sources (
    source_name,
    source_type,
    domain,
    owner_team,
    expected_daily_records,
    freshness_sla_minutes
)
values
    ('crm_accounts_api', 'api', 'sales', 'revenue-analytics', 1200, 120),
    ('payments_gateway_sftp', 'sftp', 'finance', 'payments-data', 850, 90),
    ('ad_events_partner_api', 'api', 'marketing', 'growth-analytics', 5000, 180),
    ('support_tickets_webhook', 'webhook', 'support', 'customer-ops', 650, 60)
on conflict (source_name) do update set
    source_type = excluded.source_type,
    domain = excluded.domain,
    owner_team = excluded.owner_team,
    expected_daily_records = excluded.expected_daily_records,
    freshness_sla_minutes = excluded.freshness_sla_minutes,
    is_active = true;
