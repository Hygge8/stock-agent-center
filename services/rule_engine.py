"""Simple rule engine for deciding whether a candidate should enter UZI."""
from __future__ import annotations

from dataclasses import dataclass

from config.settings import settings


@dataclass(frozen=True)
class Decision:
    action: str
    depth: str | None = None
    reason: str = ""


def decide(score: float | int | None, signal: str | None = None) -> Decision:
    """Return what to do with a candidate stock.

    v0.1 rules:
    - score >= deep threshold -> UZI deep
    - score >= medium threshold -> UZI medium
    - signal contains strong watch words -> UZI deep
    - otherwise ignore
    """
    text = (signal or "").strip()
    strong_words = ["重点", "强烈", "买入", "突破", "高关注"]
    if any(word in text for word in strong_words):
        return Decision(action="uzi", depth="deep", reason=f"signal matched: {text}")

    if score is None:
        return Decision(action="ignore", reason="no score")

    value = float(score)
    if value >= settings.deep_score_threshold:
        return Decision(action="uzi", depth="deep", reason=f"score >= {settings.deep_score_threshold}")
    if value >= settings.medium_score_threshold:
        return Decision(action="uzi", depth="medium", reason=f"score >= {settings.medium_score_threshold}")
    return Decision(action="ignore", reason=f"score < {settings.medium_score_threshold}")
