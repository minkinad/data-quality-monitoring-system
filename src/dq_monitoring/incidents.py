from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import pandas as pd

from dq_monitoring.metrics import QualityMetrics

ThresholdDirection = Literal["above", "below"]


@dataclass(frozen=True)
class MetricCheck:
    metric_name: str
    threshold_key: str
    direction: ThresholdDirection
    use_abs: bool = False


METRIC_CHECKS = (
    MetricCheck("completeness_rate", "completeness_rate_min", "below"),
    MetricCheck("freshness_lag_minutes", "freshness_lag_minutes_max", "above"),
    MetricCheck("duplicate_rate", "duplicate_rate_max", "above"),
    MetricCheck("null_rate", "null_rate_max", "above"),
    MetricCheck("record_count_delta", "record_count_delta_abs_max", "above", use_abs=True),
)


def _severity_for_numeric(
    *,
    threshold_key: str,
    metric_value: float,
    thresholds: dict,
    direction: ThresholdDirection,
    use_abs: bool = False,
) -> tuple[str | None, float | None]:
    warning = thresholds["severity"]["warning"]
    critical = thresholds["severity"]["critical"]

    value = abs(metric_value) if use_abs else metric_value
    warning_threshold = float(warning[threshold_key])
    critical_threshold = float(critical[threshold_key])

    if direction == "below":
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
    incidents: list[dict] = []
    for check in METRIC_CHECKS:
        metric_value = float(metric_values[check.metric_name])
        severity, threshold_value = _severity_for_numeric(
            threshold_key=check.threshold_key,
            metric_value=metric_value,
            thresholds=thresholds,
            direction=check.direction,
            use_abs=check.use_abs,
        )
        if severity:
            incidents.append(
                _incident_row(
                    source=source,
                    metrics=metrics,
                    metric_name=check.metric_name,
                    metric_value=metric_value,
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
