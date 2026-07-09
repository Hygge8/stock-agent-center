"""Built-in lightweight stock scanner.

This module gives stock-agent-center the basic discovery role that previously
required a separate daily_stock_analysis deployment. It is intentionally simple:
fetch recent daily bars, calculate momentum/volume/trend factors, then output a
0-100 score and a human-readable signal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from config.settings import settings


@dataclass(frozen=True)
class ScanResult:
    symbol: str
    score: float
    signal: str
    reason: str
    metrics: dict[str, Any]

    def to_candidate(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "score": self.score,
            "signal": self.signal,
            "reason": self.reason,
            "metrics": self.metrics,
        }


class StockScanner:
    def __init__(self, period: str | None = None, interval: str | None = None) -> None:
        self.period = period or settings.scan_period
        self.interval = interval or settings.scan_interval

    def scan_many(self, symbols: list[str] | None = None) -> list[ScanResult]:
        symbols = symbols or settings.stock_pool
        results: list[ScanResult] = []
        for symbol in symbols:
            symbol = symbol.strip().upper()
            if not symbol:
                continue
            results.append(self.scan_one(symbol))
        return sorted(results, key=lambda item: item.score, reverse=True)

    def scan_one(self, symbol: str) -> ScanResult:
        try:
            df = yf.download(symbol, period=self.period, interval=self.interval, progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 20:
                return ScanResult(symbol=symbol, score=0, signal="数据不足", reason="not enough bars", metrics={})

            # yfinance may return multi-index columns in some cases.
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]

            close = df["Close"].dropna()
            volume = df["Volume"].dropna() if "Volume" in df else pd.Series(dtype=float)
            if len(close) < 20:
                return ScanResult(symbol=symbol, score=0, signal="数据不足", reason="not enough close bars", metrics={})

            last = float(close.iloc[-1])
            ret_5 = self._return(close, 5)
            ret_20 = self._return(close, 20)
            ret_60 = self._return(close, 60)
            sma_20 = float(close.tail(20).mean())
            sma_60 = float(close.tail(min(60, len(close))).mean())
            vol_20 = float(close.pct_change().tail(20).std() * np.sqrt(252)) if len(close) >= 21 else 0.0
            vol_ratio = self._volume_ratio(volume)

            score = 50.0
            score += self._clip(ret_5 * 180, -10, 12)
            score += self._clip(ret_20 * 140, -18, 22)
            score += self._clip(ret_60 * 80, -15, 18)
            score += 8 if last > sma_20 else -6
            score += 8 if last > sma_60 else -6
            score += self._clip((vol_ratio - 1) * 8, -4, 8)
            score -= self._clip(vol_20 * 10, 0, 12)
            score = round(float(max(0, min(100, score))), 1)

            if score >= settings.deep_score_threshold:
                signal = "重点关注"
            elif score >= settings.medium_score_threshold:
                signal = "观察"
            else:
                signal = "暂不进入深度"

            reason = f"5日{ret_5:.1%}，20日{ret_20:.1%}，60日{ret_60:.1%}，量比{vol_ratio:.2f}"
            metrics = {
                "last": round(last, 4),
                "return_5d": round(ret_5, 4),
                "return_20d": round(ret_20, 4),
                "return_60d": round(ret_60, 4),
                "sma_20": round(sma_20, 4),
                "sma_60": round(sma_60, 4),
                "volatility_20d_annualized": round(vol_20, 4),
                "volume_ratio": round(vol_ratio, 4),
            }
            return ScanResult(symbol=symbol, score=score, signal=signal, reason=reason, metrics=metrics)
        except Exception as exc:
            return ScanResult(symbol=symbol, score=0, signal="扫描失败", reason=str(exc), metrics={})

    @staticmethod
    def _return(close: pd.Series, days: int) -> float:
        if len(close) <= days:
            return 0.0
        previous = float(close.iloc[-days - 1])
        if previous == 0:
            return 0.0
        return float(close.iloc[-1] / previous - 1)

    @staticmethod
    def _volume_ratio(volume: pd.Series) -> float:
        if volume.empty or len(volume) < 20:
            return 1.0
        recent = float(volume.tail(5).mean())
        base = float(volume.tail(20).mean())
        if base <= 0:
            return 1.0
        return recent / base

    @staticmethod
    def _clip(value: float, low: float, high: float) -> float:
        return float(max(low, min(high, value)))
