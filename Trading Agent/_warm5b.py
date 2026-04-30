"""Pre-warm with per-stock timing, token count, and cost tracking."""
import os, sys, time, json
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()

TICKERS = ["ICICIBANK", "INFY"]  # resume from where it stopped
REPORTS_DIR = Path(__file__).parent / "reports"
trade_date = date.today().isoformat()

# DeepSeek pricing (per 1M tokens)
DEEPSEEK_INPUT_PRICE  = 0.27   # $ per 1M input tokens
DEEPSEEK_OUTPUT_PRICE = 1.10   # $ per 1M output tokens

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

results = []
TOTAL_START = time.time()

for i, ticker in enumerate(TICKERS):
    ticker_ns = f"{ticker}.NS"
    config["results_dir"] = str(REPORTS_DIR / ticker)
    print(f"[{i+1}/{len(TICKERS)}] {ticker} ...", end=" ", flush=True)

    t0 = time.time()
    try:
        ta = TradingAgentsGraph(debug=False, config=config)
        final_state, signal = ta.propagate(ticker_ns, trade_date)
        t1 = time.time()

        supplementary = {
            "bse_announcements": get_bse_announcements(ticker_ns, look_back, trade_date),
            "bse_bulk_deals": get_bse_bulk_deals(ticker_ns),
            "fii_dii": fii_dii,
            "reddit_sentiment": get_india_reddit_sentiment(ticker_ns, look_back, trade_date),
        }

        report_path = generate_report(ticker=ticker_ns, trade_date=trade_date, final_state=final_state, signal=signal, supplementary=supplementary)
        save_trade_csv(report_path, ticker_ns, signal, final_state.get("final_trade_decision",""))
        write_cache(ticker_ns, trade_date, final_state, signal, supplementary)

        # Estimate tokens and cost from langchain callback / response metadata
        input_tokens = 0
        output_tokens = 0
        for msg in final_state.get("messages", []):
            if hasattr(msg, "usage_metadata"):
                um = msg.usage_metadata
                input_tokens += um.get("input_tokens", 0)
                output_tokens += um.get("output_tokens", 0)
            elif hasattr(msg, "response_metadata"):
                rm = msg.response_metadata
                if "token_usage" in rm:
                    tu = rm["token_usage"]
                    input_tokens += tu.get("prompt_tokens", 0)
                    output_tokens += tu.get("completion_tokens", 0)

        elapsed = t1 - t0
        cost = (input_tokens / 1e6 * DEEPSEEK_INPUT_PRICE) + (output_tokens / 1e6 * DEEPSEEK_OUTPUT_PRICE)

        row = {
            "ticker": ticker, "signal": signal, "elapsed_sec": round(elapsed),
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost, 4),
        }
        results.append(row)
        print(f"OK ({signal})  {elapsed:.0f}s  {input_tokens}+{output_tokens} tok  ${cost:.4f}")

    except Exception as e:
        elapsed = time.time() - t0
        row = {"ticker": ticker, "signal": "FAIL", "elapsed_sec": round(elapsed), "error": str(e)[:100]}
        results.append(row)
        print(f"FAIL ({e})")

TOTAL_END = time.time()
total_cost = sum(r.get("cost_usd", 0) for r in results)
total_tokens = sum(r.get("total_tokens", 0) for r in results)

print(f"\n{'='*60}")
print(f"Total time: {(TOTAL_END-TOTAL_START)/60:.1f} min")
print(f"Total tokens: {total_tokens:,}")
print(f"Total cost: ${total_cost:.4f}")
print(f"\nPer-stock breakdown:")
for r in results:
    if r["signal"] == "FAIL":
        print(f"  {r['ticker']:<12} FAIL  ({r.get('error','?')})")
    else:
        print(f"  {r['ticker']:<12} {r['signal']:<12} {r['elapsed_sec']}s  {r['input_tokens']}+{r['output_tokens']} tok  ${r['cost_usd']:.4f}")

# Save results
(REPORTS_DIR / "cache" / f"_warm_stats_{trade_date}.json").write_text(json.dumps(results, indent=2, default=str))
