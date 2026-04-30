"""Basket analysis — upload a portfolio CSV, cross-reference with FII/DII flow."""
import csv
import io
from typing import Optional

import yfinance as yf

from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity


def _get_fii_dii_raw(curr_date: str) -> Optional[dict]:
    """Fetch raw FII/DII data as a dict."""
    try:
        import requests

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        resp = session.get("https://www.nseindia.com/api/fiidiiTradeReact", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        result = {}
        for entry in data:
            cat = entry.get("category", "").upper()
            net = float(entry.get("netValue", 0))
            if "FII" in cat or "FPI" in cat:
                result["fii_net"] = net
            elif "DII" in cat:
                result["dii_net"] = net
        return result
    except Exception:
        return None


def _fetch_quick_metrics(ticker_ns: str) -> dict:
    """Fetch basic price, PE, market cap for a stock."""
    try:
        info = yf.Ticker(ticker_ns).info
        return {
            "name": info.get("longName", ticker_ns),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "pe": info.get("trailingPE"),
            "mcap": info.get("marketCap"),
        }
    except Exception:
        return {"name": ticker_ns, "price": None, "pe": None, "mcap": None}


def analyse_basket(portfolio_csv: str, curr_date: str) -> tuple[list[dict], dict]:
    """Analyse a portfolio CSV against FII/DII data.

    CSV format: symbol,quantity,buy_price
    Returns: (rows, summary) where rows is a list of enriched dicts
    """
    reader = csv.DictReader(io.StringIO(portfolio_csv))
    # Normalise header names
    rows = []
    fii_dii = _get_fii_dii_raw(curr_date)

    for row in reader:
        symbol = (row.get("symbol") or row.get("Symbol") or row.get("ticker") or "").strip().upper()
        if not symbol:
            continue
        ticker_ns = f"{symbol}.NS" if not symbol.endswith((".NS", ".BO")) else symbol

        metrics = _fetch_quick_metrics(ticker_ns)

        qty = row.get("quantity") or row.get("Quantity") or row.get("qty") or ""
        buy_price = row.get("buy_price") or row.get("Buy Price") or row.get("price") or ""

        fii_net = fii_dii.get("fii_net") if fii_dii else None
        dii_net = fii_dii.get("dii_net") if fii_dii else None

        # Determine sentiment based on FII/DII (stock-level proxy)
        if fii_net and fii_net > 0:
            sentiment = "Bullish"
        elif dii_net and dii_net > 0:
            sentiment = "Cautious"
        elif fii_net and fii_net < 0:
            sentiment = "Bearish"
        else:
            sentiment = "Unknown"

        rows.append({
            "symbol": symbol,
            "name": metrics.get("name", symbol),
            "price": metrics.get("price"),
            "pe": metrics.get("pe"),
            "quantity": qty,
            "buy_price": buy_price,
            "sentiment": sentiment,
        })

    summary = {
        "total_stocks": len(rows),
        "fii_net": fii_dii.get("fii_net") if fii_dii else None,
        "dii_net": fii_dii.get("dii_net") if fii_dii else None,
        "market_sentiment": (
            "Strong inflow" if (fii_dii and fii_dii.get("fii_net", 0) > 0 and fii_dii.get("dii_net", 0) > 0)
            else "Mixed" if fii_dii
            else "Unknown"
        ),
    }

    return rows, summary
