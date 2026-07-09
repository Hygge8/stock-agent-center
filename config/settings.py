"""Application settings for stock-agent-center."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, minimum: int | None = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def _csv(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    root_dir: Path = ROOT_DIR
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = _int("SERVER_PORT", 9000, minimum=1)

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///database/stock_agent.db")

    # Single deploy mode: docker-compose starts uzi-server in the same project.
    uzi_api_url: str = os.getenv("UZI_API_URL", "http://uzi-server:8977").rstrip("/")
    uzi_default_depth: str = os.getenv("UZI_DEFAULT_DEPTH", "deep")
    uzi_request_timeout: int = _int("UZI_REQUEST_TIMEOUT", 30, minimum=1)

    # Built-in stock scanner, replacing the basic discovery role of daily_stock_analysis.
    stock_pool: list[str] = None  # type: ignore[assignment]
    scan_period: str = os.getenv("SCAN_PERIOD", "3mo")
    scan_interval: str = os.getenv("SCAN_INTERVAL", "1d")
    auto_submit_scan_results: bool = _bool("AUTO_SUBMIT_SCAN_RESULTS", True)

    # Optional external daily_stock_analysis integration.
    daily_api_url: str = os.getenv("DAILY_API_URL", "http://daily-server:8000").rstrip("/")
    enable_daily_sync: bool = _bool("ENABLE_DAILY_SYNC", False)

    deep_score_threshold: int = _int("DEEP_SCORE_THRESHOLD", 85)
    medium_score_threshold: int = _int("MEDIUM_SCORE_THRESHOLD", 70)

    dingtalk_webhook_url: str = os.getenv("DINGTALK_WEBHOOK_URL", "").strip()
    dingtalk_secret: str = os.getenv("DINGTALK_SECRET", "").strip()
    enable_dingtalk_notify: bool = _bool("ENABLE_DINGTALK_NOTIFY", False)

    enable_schedule: bool = _bool("ENABLE_SCHEDULE", False)
    scan_time: str = os.getenv("SCAN_TIME", "18:00")
    schedule_depth: str = os.getenv("SCHEDULE_DEPTH", "deep")

    reports_dir: Path = ROOT_DIR / "reports"
    logs_dir: Path = ROOT_DIR / "logs"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stock_pool",
            _csv("STOCK_POOL", "VGT,SPCX,DRAM,QLD,TQQQ,NVDA,TSLA,QQQM,QQQ"),
        )
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.root_dir / "database").mkdir(parents=True, exist_ok=True)


settings = Settings()
