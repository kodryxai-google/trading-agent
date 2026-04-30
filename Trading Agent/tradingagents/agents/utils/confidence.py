"""Confidence scoring engine for trading signals.

Computes a 0-100 integer confidence score from weighted technical and
fundamental signals extracted from the analyst reports.  The score is
injected into the Trader and Portfolio Manager outputs.

Score bands:
  80-100  High confidence
  60-79   Moderate confidence
  40-59   Weak signal
  <40     Uncertain — treat with caution
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfidenceFactors:
    macd_bullish: Optional[bool] = None       # +20 / -20
    rsi_recovery: Optional[bool] = None       # +15 / -10  (RSI rising from oversold)
    above_50sma: Optional[bool] = None        # +20 / -15
    volume_confirmation: Optional[bool] = None  # +15 / -10
    news_positive: Optional[bool] = None      # +10 / -10
    fundamentals_strong: Optional[bool] = None  # +10 / -10
    anomaly_detected: bool = False            # -30
    data_inconsistency: bool = False          # -20


def compute_confidence(factors: ConfidenceFactors) -> int:
    """Return an integer 0-100 confidence score from the supplied factors."""
    score = 50  # neutral baseline

    if factors.macd_bullish is True:
        score += 20
    elif factors.macd_bullish is False:
        score -= 20

    if factors.rsi_recovery is True:
        score += 15
    elif factors.rsi_recovery is False:
        score -= 10

    if factors.above_50sma is True:
        score += 20
    elif factors.above_50sma is False:
        score -= 15

    if factors.volume_confirmation is True:
        score += 15
    elif factors.volume_confirmation is False:
        score -= 10

    if factors.news_positive is True:
        score += 10
    elif factors.news_positive is False:
        score -= 10

    if factors.fundamentals_strong is True:
        score += 10
    elif factors.fundamentals_strong is False:
        score -= 10

    if factors.anomaly_detected:
        score -= 30

    if factors.data_inconsistency:
        score -= 20

    return max(0, min(100, score))


def confidence_label(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Weak"
    return "Uncertain"


def infer_factors_from_reports(
    market_report: str = "",
    news_report: str = "",
    fundamentals_report: str = "",
    anomaly_flags: list[str] | None = None,
) -> ConfidenceFactors:
    """Heuristically infer ConfidenceFactors from analyst report text.

    This is a lightweight keyword pass — it catches clear signal words so the
    final score is grounded in the actual analysis rather than a fixed number.
    Ambiguous or missing signals stay None (no score impact).
    """
    mr = market_report.lower()
    nr = news_report.lower()
    fr = fundamentals_report.lower()

    def _search(text: str, positive_terms: list[str], negative_terms: list[str]) -> Optional[bool]:
        pos = any(t in text for t in positive_terms)
        neg = any(t in text for t in negative_terms)
        if pos and not neg:
            return True
        if neg and not pos:
            return False
        return None

    macd_bullish = _search(
        mr,
        ["macd bullish", "macd crossover", "macd positive", "macd above signal", "bullish crossover"],
        ["macd bearish", "macd negative", "macd below signal", "bearish crossover", "macd divergence"],
    )

    rsi_recovery = _search(
        mr,
        ["rsi rising", "rsi recovering", "rsi oversold", "rsi turning", "rsi below 30", "rsi bounce"],
        ["rsi overbought", "rsi above 70", "rsi falling", "rsi declining"],
    )

    above_50sma = _search(
        mr,
        ["above 50", "above the 50", "50 sma support", "50-day support", "trading above 50"],
        ["below 50", "below the 50", "50 sma resistance", "broken 50", "trading below 50"],
    )

    volume_confirmation = _search(
        mr,
        ["volume confirms", "high volume", "volume surge", "above average volume", "strong volume"],
        ["low volume", "below average volume", "weak volume", "declining volume"],
    )

    news_positive = _search(
        nr,
        ["positive", "bullish", "upgrade", "beat", "strong earnings", "growth"],
        ["negative", "bearish", "downgrade", "miss", "weak earnings", "slowdown"],
    )

    fundamentals_strong = _search(
        fr,
        ["strong revenue", "profit growth", "healthy balance", "low debt", "improving margins"],
        ["declining revenue", "loss", "high debt", "deteriorating", "writedown"],
    )

    return ConfidenceFactors(
        macd_bullish=macd_bullish,
        rsi_recovery=rsi_recovery,
        above_50sma=above_50sma,
        volume_confirmation=volume_confirmation,
        news_positive=news_positive,
        fundamentals_strong=fundamentals_strong,
        anomaly_detected=bool(anomaly_flags),
    )


def build_confidence_line(score: int) -> str:
    """Return a compact one-line confidence string for agent outputs."""
    return f"Confidence: {score}% ({confidence_label(score)})"
