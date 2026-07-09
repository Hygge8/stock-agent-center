"""Client for UZI-Skill Web API."""
from __future__ import annotations

from typing import Any

import requests

from config.settings import settings


class UziClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.uzi_api_url).rstrip("/")

    def health(self) -> dict[str, Any]:
        resp = requests.get(f"{self.base_url}/health", timeout=settings.uzi_request_timeout)
        resp.raise_for_status()
        return resp.json()

    def analyze(
        self,
        symbol: str,
        depth: str = "deep",
        notify: bool = False,
        no_resume: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "ticker": symbol.strip(),
            "depth": depth,
            "notify": notify,
            "no_resume": no_resume,
        }
        resp = requests.post(
            f"{self.base_url}/api/analyze",
            json=payload,
            timeout=settings.uzi_request_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def extract_job_id(response: dict[str, Any]) -> str | None:
        return response.get("id") or response.get("job_id") or response.get("data", {}).get("job_id")

    @staticmethod
    def extract_report_url(response: dict[str, Any]) -> str | None:
        return response.get("report_url") or response.get("absolute_url") or response.get("data", {}).get("report_url")

    @staticmethod
    def extract_status(response: dict[str, Any]) -> str:
        return str(response.get("status") or response.get("data", {}).get("status") or "submitted")
