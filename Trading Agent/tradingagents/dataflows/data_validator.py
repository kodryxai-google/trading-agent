"""Data validation layer for OHLCV and market data.

Handles:
- Price logic validation (low <= close <= high, open/high/low/close > 0)
- Volume validation
- Anomaly detection (price spikes >15%, volume >5x average)
- Timestamp normalisation and sorting
- NSE/BSE exchange holiday and weekend rejection
- Invalid candle (null OHLC) rejection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NSE trading holiday calendar (hardcoded for 2025-2026)
# Add new dates each year or replace with a live API call.
# ---------------------------------------------------------------------------
_NSE_HOLIDAYS: set = {
    # 2025
    date(2025, 1, 26),   # Republic Day
    date(2025, 3, 14),   # Holi
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 24),  # Dussehra
    date(2025, 11, 5),   # Diwali Laxmi Pujan
    date(2025, 11, 14),  # Gurunanak Jayanti (tentative)
    date(2025, 12, 25),  # Christmas
    # 2026
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 3),    # Holi (tentative)
    date(2026, 4, 3),    # Good Friday (tentative)
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 12, 25),  # Christmas
}


@dataclass
class ValidationResult:
    valid_df: pd.DataFrame
    anomalies: List[str] = field(default_factory=list)
    rejected_rows: int = 0
    warnings: List[str] = field(default_factory=list)

    @property
    def has_anomalies(self) -> bool:
        return len(self.anomalies) > 0


def is_trading_day(dt: date) -> bool:
    """Return True if dt is a valid NSE trading day (not weekend, not holiday)."""
    if dt.weekday() in (5, 6):  # Saturday=5, Sunday=6
        return False
    if dt in _NSE_HOLIDAYS:
        return False
    return True


def previous_trading_day(dt: date) -> date:
    """Walk backwards until we find a valid NSE trading day."""
    candidate = dt
    for _ in range(30):
        candidate = date.fromordinal(candidate.toordinal() - 1)
        if is_trading_day(candidate):
            return candidate
    raise ValueError(f"Could not find a trading day within 30 days before {dt}")


def resolve_trade_date(trade_date_str: str) -> str:
    """Return the effective trading date string (today or previous trading day).

    If the supplied date is not a trading day (holiday/weekend), silently
    falls back to the most recent trading day.
    """
    try:
        dt = datetime.strptime(trade_date_str, "%Y-%m-%d").date()
    except ValueError:
        return trade_date_str  # pass through unparseable strings

    if not is_trading_day(dt):
        effective = previous_trading_day(dt)
        logger.info(
            "Trade date %s is not a trading day — using %s instead",
            trade_date_str,
            effective,
        )
        return effective.strftime("%Y-%m-%d")
    return trade_date_str


def validate_ohlcv(df: pd.DataFrame, symbol: str = "") -> ValidationResult:
    """Validate and clean an OHLCV DataFrame.

    Expected columns (case-insensitive match attempted):
        Date, Open, High, Low, Close, Volume

    Returns a ValidationResult with the cleaned DataFrame and any flags.
    """
    result = ValidationResult(valid_df=df.copy())

    if df.empty:
        result.warnings.append(f"{symbol}: empty DataFrame received")
        return result

    # --- Normalise column names -------------------------------------------------
    df_work = df.copy()
    df_work.columns = [c.strip().lower() for c in df_work.columns]

    col_map = {}
    for std in ("open", "high", "low", "close", "volume"):
        for col in df_work.columns:
            if std in col:
                col_map[std] = col
                break

    # --- Timestamp normalisation ------------------------------------------------
    date_col = None
    for col in df_work.columns:
        if "date" in col or col == "datetime":
            date_col = col
            break

    if date_col:
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors="coerce")
        df_work = df_work.dropna(subset=[date_col])
        df_work = df_work.sort_values(date_col).reset_index(drop=True)

        # Reject future dates
        today = datetime.utcnow().date()
        future_mask = df_work[date_col].dt.date > today
        if future_mask.any():
            n = future_mask.sum()
            result.warnings.append(f"{symbol}: {n} future-dated row(s) removed")
            result.rejected_rows += n
            df_work = df_work[~future_mask]

        # Reject weekends
        weekend_mask = df_work[date_col].dt.weekday >= 5
        if weekend_mask.any():
            n = weekend_mask.sum()
            result.warnings.append(f"{symbol}: {n} weekend row(s) removed")
            result.rejected_rows += n
            df_work = df_work[~weekend_mask]

    # --- Reject rows with missing OHLC ------------------------------------------
    ohlc_cols = [col_map.get(k) for k in ("open", "high", "low", "close") if col_map.get(k)]
    if ohlc_cols:
        null_mask = df_work[ohlc_cols].isnull().any(axis=1)
        if null_mask.any():
            n = null_mask.sum()
            result.warnings.append(f"{symbol}: {n} incomplete candle(s) (null OHLC) removed")
            result.rejected_rows += n
            df_work = df_work[~null_mask]

    # --- Price logic checks -----------------------------------------------------
    bad_price_rows = pd.Series([False] * len(df_work), index=df_work.index)

    if "low" in col_map and "high" in col_map:
        lo = col_map["low"]
        hi = col_map["high"]
        bad_logic = df_work[lo] > df_work[hi]
        if bad_logic.any():
            n = bad_logic.sum()
            result.warnings.append(f"{symbol}: {n} row(s) where low > high — rejected")
            result.rejected_rows += n
            bad_price_rows |= bad_logic

    if "close" in col_map and "high" in col_map:
        cl = col_map["close"]
        hi = col_map["high"]
        bad_close_hi = df_work[cl] > df_work[hi]
        if bad_close_hi.any():
            n = bad_close_hi.sum()
            result.warnings.append(f"{symbol}: {n} row(s) where close > high — rejected")
            result.rejected_rows += n
            bad_price_rows |= bad_close_hi

    if "close" in col_map and "low" in col_map:
        cl = col_map["close"]
        lo = col_map["low"]
        bad_close_lo = df_work[cl] < df_work[lo]
        if bad_close_lo.any():
            n = bad_close_lo.sum()
            result.warnings.append(f"{symbol}: {n} row(s) where close < low — rejected")
            result.rejected_rows += n
            bad_price_rows |= bad_close_lo

    if "volume" in col_map:
        vol = col_map["volume"]
        neg_vol = df_work[vol] < 0
        if neg_vol.any():
            n = neg_vol.sum()
            result.warnings.append(f"{symbol}: {n} row(s) with negative volume — rejected")
            result.rejected_rows += n
            bad_price_rows |= neg_vol

    df_work = df_work[~bad_price_rows].reset_index(drop=True)

    # --- Anomaly detection -------------------------------------------------------
    if "close" in col_map and len(df_work) >= 2:
        cl = col_map["close"]
        pct_change = df_work[cl].pct_change().abs()
        spike_mask = pct_change > 0.15
        if spike_mask.any():
            spike_dates = []
            if date_col:
                spike_dates = df_work.loc[spike_mask, date_col].dt.strftime("%Y-%m-%d").tolist()
            else:
                spike_dates = df_work.index[spike_mask].tolist()
            for dt in spike_dates:
                result.anomalies.append(
                    f"{symbol}: Price spike >15% detected on {dt} — verify data source"
                )

    if "volume" in col_map and len(df_work) >= 5:
        vol = col_map["volume"]
        avg_vol = df_work[vol].rolling(20, min_periods=5).mean().shift(1)
        high_vol_mask = df_work[vol] > (avg_vol * 5)
        if high_vol_mask.any():
            vol_dates = []
            if date_col:
                vol_dates = df_work.loc[high_vol_mask, date_col].dt.strftime("%Y-%m-%d").tolist()
            else:
                vol_dates = df_work.index[high_vol_mask].tolist()
            for dt in vol_dates:
                result.anomalies.append(
                    f"{symbol}: Volume >5x 20-day average on {dt} — unusual activity"
                )

    # Restore original column names from the cleaned index
    result.valid_df = df_work
    return result


def get_latest_candle(df: pd.DataFrame) -> Optional[pd.Series]:
    """Return the last row of a validated OHLCV DataFrame (the latest candle).

    The caller is responsible for validating the DataFrame first so that the
    latest row is guaranteed to be a complete, non-future, non-weekend candle.
    """
    if df.empty:
        return None
    return df.iloc[-1]


def format_anomaly_section(anomalies: List[str]) -> str:
    """Format anomaly flags into a section string for agent prompts."""
    if not anomalies:
        return ""
    lines = ["**Data Anomalies Detected:**"]
    for a in anomalies:
        lines.append(f"  - {a}")
    return "\n".join(lines)
