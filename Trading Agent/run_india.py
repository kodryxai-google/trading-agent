"""India Trading Agent entry point.

Usage:
    python run_india.py --ticker TCS
    python run_india.py --ticker RELIANCE --date 2026-04-29
"""
import argparse
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.india_bse import get_bse_announcements, get_bse_bulk_deals
from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity
from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
from tradingagents.dataflows.india_report import generate_report


def build_config(ticker_ns: str) -> dict:
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "clodio"
    config["backend_url"] = None
    config["deep_think_llm"] = "deepseek-ai/DeepSeek-V4-Pro"
    config["quick_think_llm"] = "deepseek-ai/DeepSeek-V4-Pro"
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
    trade_date = args.date
    look_back = "2026-04-01"

    print(f"\n{'='*60}")
    print(f"  India Trading Agent — {ticker_ns}")
    print(f"  Date: {trade_date}")
    print(f"  LLM: DeepSeek V4 Pro via clod.io")
    print(f"{'='*60}\n")

    config = build_config(ticker_ns)
    ta = TradingAgentsGraph(debug=True, config=config)

    print("Running multi-agent analysis...\n")
    final_state, signal = ta.propagate(ticker_ns, trade_date)

    print("\nFetching supplementary India data...")
    supplementary = {
        "bse_announcements": get_bse_announcements(ticker_ns, look_back, trade_date),
        "bse_bulk_deals":    get_bse_bulk_deals(ticker_ns),
        "fii_dii":           get_fii_dii_activity(trade_date),
        "reddit_sentiment":  get_india_reddit_sentiment(ticker_ns, look_back, trade_date),
    }

    print("\nGenerating HTML report...")
    report_path = generate_report(
        ticker=ticker_ns,
        trade_date=trade_date,
        final_state=final_state,
        signal=signal,
        supplementary=supplementary,
    )

    print(f"\n{'='*60}")
    print(f"  Signal: {signal}")
    print(f"  Report: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
