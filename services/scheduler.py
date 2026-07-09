"""Optional scheduler for stock-agent-center."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config.settings import settings
from services.stock_scanner import StockScanner
from services.uzi_client import UziClient
from services.rule_engine import decide

logger = logging.getLogger(__name__)


def start_scheduler() -> BackgroundScheduler | None:
    if not settings.enable_schedule:
        return None

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    hour, minute = _parse_scan_time(settings.scan_time)

    def submit_scheduled_scan() -> None:
        scanner = StockScanner()
        client = UziClient()
        results = scanner.scan_many(settings.stock_pool)
        for result in results:
            decision = decide(result.score, result.signal)
            if decision.action == "uzi" and decision.depth:
                depth = settings.schedule_depth or decision.depth
                try:
                    client.analyze(symbol=result.symbol, depth=depth, notify=False)
                    logger.info("scheduled UZI submitted: %s %s score=%s", result.symbol, depth, result.score)
                except Exception as exc:
                    logger.warning("scheduled UZI submit failed: %s %s", result.symbol, exc)

    scheduler.add_job(submit_scheduled_scan, "cron", hour=hour, minute=minute, id="scheduled_stock_scan")
    scheduler.start()
    return scheduler


def _parse_scan_time(value: str) -> tuple[int, int]:
    try:
        hour, minute = value.split(":", 1)
        return int(hour), int(minute)
    except Exception:
        return 18, 0
