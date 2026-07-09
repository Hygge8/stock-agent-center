"""Optional scheduler for stock-agent-center."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from config.settings import settings
from services.uzi_client import UziClient


def start_scheduler() -> BackgroundScheduler | None:
    if not settings.enable_schedule:
        return None

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    hour, minute = _parse_scan_time(settings.scan_time)

    def submit_scheduled_jobs() -> None:
        client = UziClient()
        for symbol in settings.schedule_tickers:
            client.analyze(symbol=symbol, depth=settings.schedule_depth, notify=False)

    scheduler.add_job(submit_scheduled_jobs, "cron", hour=hour, minute=minute, id="scheduled_uzi_jobs")
    scheduler.start()
    return scheduler


def _parse_scan_time(value: str) -> tuple[int, int]:
    try:
        hour, minute = value.split(":", 1)
        return int(hour), int(minute)
    except Exception:
        return 18, 0
