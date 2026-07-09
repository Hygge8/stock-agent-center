"""DingTalk notification service."""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from urllib.parse import quote_plus

import requests

from config.settings import settings


class DingTalkNotifier:
    @property
    def configured(self) -> bool:
        return bool(settings.dingtalk_webhook_url)

    def _signed_url(self) -> str:
        webhook = settings.dingtalk_webhook_url
        secret = settings.dingtalk_secret
        if not secret:
            return webhook
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
        sign = quote_plus(base64.b64encode(digest).decode("utf-8"))
        separator = "&" if "?" in webhook else "?"
        return f"{webhook}{separator}timestamp={timestamp}&sign={sign}"

    def send_text(self, content: str) -> tuple[bool, str]:
        if not settings.enable_dingtalk_notify:
            return True, "DingTalk notify disabled"
        if not self.configured:
            return False, "DINGTALK_WEBHOOK_URL is not configured"
        if "股票" not in content:
            content = f"股票：{content}"
        try:
            resp = requests.post(
                self._signed_url(),
                json={"msgtype": "text", "text": {"content": content}},
                timeout=12,
            )
            data = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                return False, f"HTTP {resp.status_code}: {data}"
            if data.get("errcode") not in (0, None):
                return False, f"DingTalk errcode={data.get('errcode')}, errmsg={data.get('errmsg')}"
            return True, data.get("errmsg") or "ok"
        except Exception as exc:
            return False, str(exc)

    def notify_candidate_submitted(self, symbol: str, score: float | None, depth: str, job_id: str | None) -> tuple[bool, str]:
        return self.send_text(
            "股票深度研究任务已提交\n"
            f"标的：{symbol}\n"
            f"评分：{score if score is not None else '-'}\n"
            f"深度：{depth}\n"
            f"任务：{job_id or '-'}"
        )
