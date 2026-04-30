"""Nightly Nifty 50 pre-warmer — batch-analyse all Nifty 50 stocks and cache results."""
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Nifty 50 tickers (April 2026)
NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
    "ITC", "KOTAKBANK", "BHARTIARTL", "SBIN", "LT", "BAJFINANCE",
    "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", "HCLTECH",
    "WIPRO", "ULTRACEMCO", "ADANIPORTS", "ADANIENT", "NTPC", "POWERGRID",
    "ONGC", "COALINDIA", "JSWSTEEL", "TATASTEEL", "HINDALCO",
    "TECHM", "DIVISLAB", "DRREDDY", "CIPLA", "APOLLOHOSP",
    "GRASIM", "BAJAJFINSV", "INDUSINDBK", "EICHERMOT", "HEROMOTOCO",
    "BRITANNIA", "NESTLEIND", "BAJAJ-AUTO", "BEL", "TRENT",
    "HDFCLIFE", "SBILIFE", "TATACONSUM", "TATAMOTORS", "BPCL", "M&M",
]

REPORTS_DIR = Path(__file__).parent / "reports"
CACHE_DIR = REPORTS_DIR / "cache"


def _sleep(seconds: int = 30) -> None:
    """Sleep between stocks to avoid rate limits."""
    import time
    time.sleep(seconds)


def main():
    trade_date = date.today().isoformat()
    print(f"Scheduler: Nifty 50 pre-warm for {trade_date}")
    print(f"{"="*60}")

    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.dataflows.india_bse import get_bse_announcements, get_bse_bulk_deals
    from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity
    from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
    from tradingagents.dataflows.india_report import generate_report
    from tradingagents.utils.cache import write_cache

    # Build config once
    config = DEFAULT_CONFIG.copy()
    if os.environ.get("DEEPSEEK_API_KEY"):
        config["llm_provider"] = "deepseek"
        config["deep_think_llm"] = "deepseek-chat"
        config["quick_think_llm"] = "deepseek-chat"
    elif os.environ.get("GOOGLE_API_KEY"):
        config["llm_provider"] = "google"
        config["deep_think_llm"] = "gemini-2.5-flash"
        config["quick_think_llm"] = "gemini-2.5-flash"
    else:
        print("ERROR: No LLM API key configured")
        sys.exit(1)

    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "india",
    }

    # Shared supplementary data (FII/DII is same for all stocks)
    print("Fetching FII/DII data...")
    look_back = "2026-04-01"
    fii_dii = get_fii_dii_activity(trade_date)

    succeed = 0
    fail = 0

    for i, ticker in enumerate(NIFTY_50):
        ticker_ns = f"{ticker}.NS"
        config["results_dir"] = str(REPORTS_DIR / ticker)

        try:
            print(f"[{i+1:2d}/{len(NIFTY_50)}] {ticker} ...", end=" ", flush=True)

            ta = TradingAgentsGraph(debug=False, config=config)
            final_state, signal = ta.propagate(ticker_ns, trade_date)

            supplementary = {
                "bse_announcements": get_bse_announcements(ticker_ns, look_back, trade_date),
                "bse_bulk_deals": get_bse_bulk_deals(ticker_ns),
                "fii_dii": fii_dii,
                "reddit_sentiment": get_india_reddit_sentiment(ticker_ns, look_back, trade_date),
            }

            report_path = generate_report(
                ticker=ticker_ns,
                trade_date=trade_date,
                final_state=final_state,
                signal=signal,
                supplementary=supplementary,
            )

            write_cache(ticker_ns, trade_date, final_state, signal, supplementary)
            print(f"OK ({signal})")
            succeed += 1

        except Exception as e:
            print(f"FAIL ({e})")
            fail += 1

        # Brief pause between stocks
        if i < len(NIFTY_50) - 1:
            _sleep(5)

    print(f"\n{'='*60}")
    print(f"Done: {succeed} succeeded, {fail} failed")
    print(f"Cache: {CACHE_DIR}")

    # Write status file
    status_path = CACHE_DIR / "status.json"
    status_path.write_text(json.dumps({
        "last_run": datetime.now().isoformat(),
        "date": trade_date,
        "succeeded": succeed,
        "failed": fail,
        "total": len(NIFTY_50),
    }, indent=2))


if __name__ == "__main__":
    main()
