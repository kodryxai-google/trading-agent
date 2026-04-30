"""India Trading Agent entry point.

Usage:
    python run_india.py --ticker TCS
    python run_india.py --ticker RELIANCE --date 2026-04-29
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

# Force UTF-8 output on Windows terminals that default to cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.india_bse import get_bse_announcements, get_bse_bulk_deals
from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity
from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
from tradingagents.dataflows.india_report import generate_report
from tradingagents.dataflows.data_validator import resolve_trade_date
from tradingagents.dataflows.y_finance import reset_anomaly_log, get_anomaly_log


def build_config(ticker_ns: str) -> dict:
    config = DEFAULT_CONFIG.copy()
    # Primary: DeepSeek V4, fallback: Google Gemini
    if os.environ.get("DEEPSEEK_API_KEY"):
        config["llm_provider"] = "deepseek"
        config["backend_url"] = None
        config["deep_think_llm"] = "deepseek-chat"
        config["quick_think_llm"] = "deepseek-chat"
    elif os.environ.get("GOOGLE_API_KEY"):
        config["llm_provider"] = "google"
        config["backend_url"] = None
        config["deep_think_llm"] = "gemini-2.5-flash"
        config["quick_think_llm"] = "gemini-2.5-flash"
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1
    config["results_dir"] = str(Path("reports") / ticker_ns.replace(".NS", ""))
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "india",
    }
    return config


def main():
    parser = argparse.ArgumentParser(description="India Stock Trading Agent")
    parser.add_argument("--ticker", required=True, help="NSE ticker (e.g. TCS, RELIANCE)")
    parser.add_argument("--date", default=str(date.today()), help="Trade date YYYY-MM-DD")
    args = parser.parse_args()

    ticker_base = args.ticker.upper().replace(".NS", "").replace(".BO", "")
    ticker_ns = f"{ticker_base}.NS"

    # Resolve to a valid NSE trading day (skips holidays and weekends)
    trade_date = resolve_trade_date(args.date)
    if trade_date != args.date:
        print(f"  Note: {args.date} is not a trading day — using {trade_date}")

    look_back = "2026-04-01"

    # Reset the anomaly accumulator for this fresh run
    reset_anomaly_log()

    print(f"\n{'='*60}")
    print(f"  India Trading Agent — {ticker_ns}")
    print(f"  Date: {trade_date}")
    print(f"  LLM: Gemini 2.5 Flash (Google)")
    print(f"{'='*60}\n")

    config = build_config(ticker_ns)
    ta = TradingAgentsGraph(debug=True, config=config)

    print("Running multi-agent analysis...\n")
    final_state, signal = ta.propagate(ticker_ns, trade_date)

    # Attach any anomalies collected during data fetching to the final state
    # so they appear in the report and were visible to the Trader's confidence scoring.
    anomalies = get_anomaly_log()
    if anomalies:
        print(f"\n  [{len(anomalies)} data anomaly flag(s) detected — see report]")
        for a in anomalies:
            print(f"    * {a}")

    print("\nFetching supplementary India data...")
    supplementary = {
        "bse_announcements": get_bse_announcements(ticker_ns, look_back, trade_date),
        "bse_bulk_deals":    get_bse_bulk_deals(ticker_ns),
        "fii_dii":           get_fii_dii_activity(trade_date),
        "reddit_sentiment":  get_india_reddit_sentiment(ticker_ns, look_back, trade_date),
    }

    # Persist FII/DII to DuckDB
    try:
        import re as _re
        fii_text = supplementary.get("fii_dii", "")
        _fii_net = _fii_buy = _fii_sell = _dii_net = _dii_buy = _dii_sell = None
        for ln in fii_text.split("\n"):
            def _parse_cr(s):
                m = _re.search(r"Rs\.([\d,]+\.?\d*)", s)
                return float(m.group(1).replace(",", "")) if m else None
            if "FII/FPI Net:" in ln:
                _fii_net = _parse_cr(ln)
                _sign = -1 if "SELLING" in ln.upper() else 1
                if _fii_net: _fii_net *= _sign
            elif "Buy:" in ln and _fii_net is not None and _fii_buy is None:
                parts = ln.split("|")
                _fii_buy  = _parse_cr(parts[0]) if len(parts) > 0 else None
                _fii_sell = _parse_cr(parts[1]) if len(parts) > 1 else None
            elif "DII Net:" in ln:
                _dii_net = _parse_cr(ln)
                _sign = -1 if "SELLING" in ln.upper() else 1
                if _dii_net: _dii_net *= _sign
            elif "Buy:" in ln and _dii_net is not None and _dii_buy is None:
                parts = ln.split("|")
                _dii_buy  = _parse_cr(parts[0]) if len(parts) > 0 else None
                _dii_sell = _parse_cr(parts[1]) if len(parts) > 1 else None
        from tradingagents.storage.db import TradingDB
        db_path = config.get("db_path")
        if db_path:
            with TradingDB(db_path) as _db:
                _db.write_fii_dii(
                    trade_date=trade_date,
                    fii_net=_fii_net, fii_buy=_fii_buy, fii_sell=_fii_sell,
                    dii_net=_dii_net, dii_buy=_dii_buy, dii_sell=_dii_sell,
                )
    except Exception as _e:
        print(f"  [DuckDB FII/DII write skipped: {_e}]")

    print("\nGenerating HTML report...")
    report_path = generate_report(
        ticker=ticker_ns,
        trade_date=trade_date,
        final_state=final_state,
        signal=signal,
        supplementary=supplementary,
        data_anomalies=anomalies,
    )

    # Write daily brief to Obsidian
    try:
        from tradingagents.storage.obsidian import ObsidianVault
        vault_path = config.get("obsidian_vault_path")
        if vault_path:
            from tradingagents.agents.utils.confidence import (
                infer_factors_from_reports, compute_confidence, confidence_label
            )
            _mkt  = final_state.get("market_report", "")
            _news = final_state.get("news_report", "")
            _fund = final_state.get("fundamentals_report", "")
            _fac  = infer_factors_from_reports(_mkt, _news, _fund, anomalies)
            _conf = compute_confidence(_fac)
            vault = ObsidianVault(vault_path)
            vault.write_daily_brief(
                trade_date=trade_date,
                runs=[{"ticker": ticker_base, "signal": signal, "confidence": _conf}],
            )
    except Exception as _e:
        print(f"  [Obsidian daily brief skipped: {_e}]")

    print(f"\n{'='*60}")
    print(f"  Signal: {signal}")
    print(f"  Report: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
