from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from dq_monitoring.metrics import QualityMetrics


def _severity_for_numeric(
    *,
    metric_name: str,
    metric_value: float,
    thresholds: dict,
    lower_is_bad: bool = False,
    use_abs: bool = False,
) -> tuple[str | None, float | None]:
    warning = thresholds["severity"]["warning"]
    critical = thresholds["severity"]["critical"]

    value = abs(metric_value) if use_abs else metric_value
    warning_threshold = float(warning[metric_name])
    critical_threshold = float(critical[metric_name])

    if lower_is_bad:
        if value < critical_threshold:
            return "critical", critical_threshold
        if value < warning_threshold:
            return "warning", warning_threshold
    else:
        if value > critical_threshold:
            return "critical", critical_threshold
        if value > warning_threshold:
            return "warning", warning_threshold

    return None, None


def build_incidents(source: pd.Series, metrics: QualityMetrics, thresholds: dict) -> pd.DataFrame:
    metric_values = asdict(metrics)
    checks = [
        ("completeness_rate", True, False),
        ("freshness_lag_minutes", False, False),
        ("duplicate_rate", False, False),
        ("null_rate", False, False),
        ("record_count_delta", False, True),
    ]

    incidents: list[dict] = []
    for metric_name, lower_is_bad, use_abs in checks:
        threshold_key = (
            f"{metric_name}_min"
            if metric_name == "completeness_rate"
            else f"{metric_name}_abs_max"
            if metric_name == "record_count_delta"
            else f"{metric_name}_max"
        )
        severity, threshold_value = _severity_for_numeric(
            metric_name=threshold_key,
            metric_value=float(metric_values[metric_name]),
            thresholds=thresholds,
            lower_is_bad=lower_is_bad,
            use_abs=use_abs,
        )
        if severity:
            incidents.append(
                _incident_row(
                    source=source,
                    metrics=metrics,
                    metric_name=metric_name,
                    metric_value=float(metric_values[metric_name]),
                    threshold_value=threshold_value,
                    severity=severity,
                )
            )

    if metrics.schema_drift_flag:
        incidents.append(
            _incident_row(
                source=source,
                metrics=metrics,
                metric_name="schema_drift_flag",
                metric_value=1.0,
                threshold_value=0.0,
                severity="warning",
            )
        )

    if metrics.failed_jobs_count > thresholds["global"]["failed_jobs_count_max"]:
        incidents.append(
            _incident_row(
                source=source,
                metrics=metrics,
                metric_name="failed_jobs_count",
                metric_value=float(metrics.failed_jobs_count),
                threshold_value=float(thresholds["global"]["failed_jobs_count_max"]),
                severity="critical",
            )
        )

    return pd.DataFrame(incidents)


def _incident_row(
    *,
    source: pd.Series,
    metrics: QualityMetrics,
    metric_name: str,
    metric_value: float,
    threshold_value: float | None,
    severity: str,
) -> dict:
    source_name = str(source.source_name)
    title = f"{severity.upper()}: {source_name} breached {metric_name}"
    details = (
        f"Source {source_name} breached {metric_name} on {metrics.batch_date}. "
        f"Observed value: {metric_value:.4f}; threshold: {threshold_value}."
    )
    return {
        "source_id": metrics.source_id,
        "batch_date": metrics.batch_date,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "threshold_value": threshold_value,
        "severity": severity,
        "status": "open",
        "title": title,
        "details": details,
    }
