from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from os import getenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_url: str
    dq_env: str = "local"


def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        database_url=getenv(
            "DATABASE_URL",
            "postgresql+psycopg://dq_user:dq_password@localhost:5432/dq_monitoring",
        ),
        dq_env=getenv("DQ_ENV", "local"),
    )


def load_thresholds(path: Path | None = None) -> dict[str, Any]:
    threshold_path = path or PROJECT_ROOT / "config" / "thresholds.yml"
    with threshold_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)
