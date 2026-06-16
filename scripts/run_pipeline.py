#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dq_monitoring.db import get_engine, reset_database  # noqa: E402
from dq_monitoring.pipeline import run_pipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run data quality monitoring demo pipeline")
    parser.add_argument("--days", type=int, default=30, help="Number of days to generate")
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=None,
        help="First batch date in YYYY-MM-DD format",
    )
    parser.add_argument("--reset", action="store_true", help="Drop and recreate demo schema")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = get_engine()

    if args.reset:
        reset_database(engine)

    start_date = args.start_date or date.today() - timedelta(days=args.days)
    stats = run_pipeline(engine, start_date=start_date, days=args.days)
    print(
        "Pipeline finished: "
        f"jobs={stats['jobs']}, records={stats['records']}, "
        f"metrics={stats['metrics']}, incidents={stats['incidents']}"
    )


if __name__ == "__main__":
    main()
