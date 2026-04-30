"""Layer 1 — DuckDB time-series store for OHLCV, indicators, signals, anomalies, FII/DII."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS ohlcv (
    ticker      VARCHAR NOT NULL,
    trade_date  DATE    NOT NULL,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      BIGINT,
    PRIMARY KEY (ticker, trade_date)
);

CREATE TABLE IF NOT EXISTS indicators (
    ticker      VARCHAR NOT NULL,
    trade_date  DATE    NOT NULL,
    name        VARCHAR NOT NULL,
    value       DOUBLE,
    PRIMARY KEY (ticker, trade_date, name)
);

CREATE TABLE IF NOT EXISTS signals (
    ticker      VARCHAR  NOT NULL,
    trade_date  DATE     NOT NULL,
    signal      VARCHAR  NOT NULL,
    confidence  INTEGER,
    tech_signal VARCHAR,
    fund_signal VARCHAR,
    macro_signal VARCHAR,
    pm_signal   VARCHAR,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, trade_date)
);

CREATE TABLE IF NOT EXISTS anomalies (
    id          INTEGER PRIMARY KEY,
    ticker      VARCHAR  NOT NULL,
    trade_date  DATE     NOT NULL,
    description VARCHAR  NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS anomaly_seq;

CREATE TABLE IF NOT EXISTS fii_dii (
    trade_date  DATE    NOT NULL PRIMARY KEY,
    fii_net     DOUBLE,
    fii_buy     DOUBLE,
    fii_sell    DOUBLE,
    dii_net     DOUBLE,
    dii_buy     DOUBLE,
    dii_sell    DOUBLE
);
"""


class TradingDB:
    """DuckDB-backed store. Call close() or use as a context manager."""

    def __init__(self, db_path: str | Path):
        self._path = str(db_path)
        self._con: Optional[duckdb.DuckDBPyConnection] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> "TradingDB":
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._con = duckdb.connect(self._path)
        self._con.execute(_DDL)
        return self

    def close(self):
        if self._con:
            self._con.close()
            self._con = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *_):
        self.close()

    @property
    def con(self) -> duckdb.DuckDBPyConnection:
        if self._con is None:
            self.connect()
        return self._con

    # ------------------------------------------------------------------
    # OHLCV
    # ------------------------------------------------------------------

    def upsert_ohlcv(self, ticker: str, df: pd.DataFrame) -> int:
        """Insert or replace OHLCV rows. Returns row count written."""
        if df is None or df.empty:
            return 0
        rows = []
        for idx, row in df.iterrows():
            d = idx.date() if hasattr(idx, "date") else idx
            rows.append((
                ticker, d,
                _safe(row, "Open"), _safe(row, "High"),
                _safe(row, "Low"),  _safe(row, "Close"),
                _int(row, "Volume"),
            ))
        self.con.executemany(
            "INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)", rows
        )
        logger.debug("upsert_ohlcv: %d rows for %s", len(rows), ticker)
        return len(rows)

    # ------------------------------------------------------------------
    # Indicators
    # ------------------------------------------------------------------

    def write_indicator(self, ticker: str, trade_date: date | str, name: str, value: float):
        d = _to_date(trade_date)
        self.con.execute(
            "INSERT OR REPLACE INTO indicators VALUES (?,?,?,?)",
            [ticker, d, name, value],
        )

    def write_indicators_bulk(self, ticker: str, trade_date: date | str, kvs: dict):
        d = _to_date(trade_date)
        rows = [(ticker, d, k, v) for k, v in kvs.items() if v is not None]
        if rows:
            self.con.executemany(
                "INSERT OR REPLACE INTO indicators VALUES (?,?,?,?)", rows
            )

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def write_signal(
        self,
        ticker: str,
        trade_date: date | str,
        signal: str,
        confidence: Optional[int] = None,
        tech_signal: Optional[str] = None,
        fund_signal: Optional[str] = None,
        macro_signal: Optional[str] = None,
        pm_signal: Optional[str] = None,
    ):
        d = _to_date(trade_date)
        self.con.execute(
            """INSERT OR REPLACE INTO signals
               (ticker, trade_date, signal, confidence, tech_signal, fund_signal, macro_signal, pm_signal)
               VALUES (?,?,?,?,?,?,?,?)""",
            [ticker, d, signal, confidence, tech_signal, fund_signal, macro_signal, pm_signal],
        )

    # ------------------------------------------------------------------
    # Anomalies
    # ------------------------------------------------------------------

    def write_anomaly(self, ticker: str, trade_date: date | str, description: str):
        d = _to_date(trade_date)
        self.con.execute(
            "INSERT INTO anomalies (id, ticker, trade_date, description) VALUES (nextval('anomaly_seq'),?,?,?)",
            [ticker, d, description],
        )

    def write_anomalies_bulk(self, ticker: str, trade_date: date | str, descriptions: list[str]):
        d = _to_date(trade_date)
        rows = [(ticker, d, desc) for desc in descriptions if desc]
        if rows:
            self.con.executemany(
                "INSERT INTO anomalies (id, ticker, trade_date, description) VALUES (nextval('anomaly_seq'),?,?,?)",
                rows,
            )

    # ------------------------------------------------------------------
    # FII/DII
    # ------------------------------------------------------------------

    def write_fii_dii(
        self,
        trade_date: date | str,
        fii_net: Optional[float] = None,
        fii_buy: Optional[float] = None,
        fii_sell: Optional[float] = None,
        dii_net: Optional[float] = None,
        dii_buy: Optional[float] = None,
        dii_sell: Optional[float] = None,
    ):
        d = _to_date(trade_date)
        self.con.execute(
            "INSERT OR REPLACE INTO fii_dii VALUES (?,?,?,?,?,?,?)",
            [d, fii_net, fii_buy, fii_sell, dii_net, dii_buy, dii_sell],
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _safe(row, col):
    try:
        v = row[col]
        return float(v) if pd.notna(v) else None
    except Exception:
        return None


def _int(row, col):
    try:
        v = row[col]
        return int(v) if pd.notna(v) else None
    except Exception:
        return None


def _to_date(d) -> date:
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])
