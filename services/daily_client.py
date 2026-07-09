"""Client for daily_stock_analysis.

v0.1 keeps this client intentionally flexible because upstream response shapes may
vary. It accepts any JSON list or common wrapper keys and normalizes candidates.
"""
from __future__ import annotations

from typing import Any

import requests

from config.settings import settings


class DailyClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.daily_api_url).rstrip("/")

    def fetch_candidates(self) -> list[dict[str, Any]]:
        resp = requests.get(f"{self.base_url}/api/candidates", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items") or data.get("data") or data.get("candidates") or []
        else:
            items = []
        return [self._normalize(item) for item in items if isinstance(item, dict)]

    @staticmethod
    def _normalize(item: dict[str, Any]) -> dict[str, Any]:
        symbol = item.get("symbol") or item.get("ticker") or item.get("code") or item.get("stock")
        score = item.get("score") or item.get("rating") or item.get("final_score")
        signal = item.get("signal") or item.get("action") or item.get("suggestion")
        return {
            "symbol": str(symbol).strip() if symbol else "",
            "score": score,
            "signal": signal,
            "raw": item,
        }
