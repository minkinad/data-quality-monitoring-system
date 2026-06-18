from __future__ import annotations

from datetime import date

import pytest

from dq_monitoring.pipeline import run_pipeline


def test_run_pipeline_rejects_non_positive_days() -> None:
    with pytest.raises(ValueError, match="days"):
        run_pipeline(object(), start_date=date(2026, 1, 1), days=0)  # type: ignore[arg-type]
