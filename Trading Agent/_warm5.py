"""Quick pre-warm — first 5 Nifty 50 stocks only."""
import os, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()

TICKERS = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY"]
REPORTS_DIR = Path(__file__).parent / "reports"
trade_date = date.today().isoformat()

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.dataflows.india_bse import get_bse_announcements, get_bse_bulk_deals
from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity
from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
from tradingagents.dataflows.india_report import generate_report
from tradingagents.utils.csv_export import save_trade_csv
from tradingagents.utils.cache import write_cache

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"
config["deep_think_llm"] = "deepseek-chat"
config["quick_think_llm"] = "deepseek-chat"
config["max_debate_rounds"] = 1
config["max_risk_discuss_rounds"] = 1
config["data_vendors"] = {"core_stock_apis":"yfinance","technical_indicators":"yfinance","fundamental_data":"yfinance","news_data":"india"}

look_back = "2026-04-01"
fii_dii = get_fii_dii_activity(trade_date)

for i, ticker in enumerate(TICKERS):
    ticker_ns = f"{ticker}.NS"
    config["results_dir"] = str(REPORTS_DIR / ticker)
    print(f"[{i+1}/5] {ticker} ...", end=" ", flush=True)
    try:
        ta = TradingAgentsGraph(debug=False, config=config)
        final_state, signal = ta.propagate(ticker_ns, trade_date)
        supplementary = {
            "bse_announcements": get_bse_announcements(ticker_ns, look_back, trade_date),
            "bse_bulk_deals": get_bse_bulk_deals(ticker_ns),
            "fii_dii": fii_dii,
            "reddit_sentiment": get_india_reddit_sentiment(ticker_ns, look_back, trade_date),
        }
        report_path = generate_report(ticker=ticker_ns, trade_date=trade_date, final_state=final_state, signal=signal, supplementary=supplementary)
        save_trade_csv(report_path, ticker_ns, signal, final_state.get("final_trade_decision",""))
        write_cache(ticker_ns, trade_date, final_state, signal, supplementary)
        print(f"OK ({signal})")
    except Exception as e:
        print(f"FAIL ({e})")

print("\nDone. 5 stocks cached. Run morning_brief.py to send Telegram.")
