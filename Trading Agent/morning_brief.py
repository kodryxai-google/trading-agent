"""Morning Brief — generates a daily Nifty 50 briefing from cached signals and sends via Telegram.
Run via Windows Task Scheduler at 8:30 AM IST daily.
"""
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = Path(__file__).parent / "reports" / "cache"

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


def _telegram_send(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram not configured")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        return r.status_code == 200 and r.json().get("ok")
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def _load_cached_signals(trade_date: str) -> dict[str, str]:
    """Load all cached Nifty 50 signals for the given date."""
    signals = {}
    for ticker in NIFTY_50:
        cp = CACHE_DIR / f"{ticker}_{trade_date}.json"
        if cp.exists():
            try:
                data = json.loads(cp.read_text())
                signals[ticker] = data.get("signal", "Unknown")
            except Exception:
                signals[ticker] = "No data"
        else:
            signals[ticker] = "Not analysed"
    return signals


def _format_signal_row(ticker: str, signal: str) -> str:
    su = signal.upper()
    if "BUY" in su or "OVERWEIGHT" in su:
        emoji = "\U0001f7e2"
    elif "SELL" in su or "UNDERWEIGHT" in su:
        emoji = "\U0001f534"
    else:
        emoji = "\U0001f7e0"
    return f"{emoji} `{ticker:<12}` *{signal}*"


def main():
    trade_date = date.today().isoformat()
    now = datetime.now().strftime("%d %b %Y, %I:%M %p IST")

    signals = _load_cached_signals(trade_date)

    # Count categories (only for analysed stocks)
    analysed_signals = {t: s for t, s in signals.items() if s not in ("Not analysed", "No data")}
    buy_count = sum(1 for s in analysed_signals.values() if any(w in s.upper() for w in ["BUY", "OVERWEIGHT"]))
    sell_count = sum(1 for s in analysed_signals.values() if any(w in s.upper() for w in ["SELL", "UNDERWEIGHT"]))
    hold_count = len(analysed_signals) - buy_count - sell_count

    # Build message
    lines = [
        "\U0001f305 *KODRYX AI — Nifty 50 Morning Brief*",
        f"_{now}_",
        "",
        f"\U0001f4ca *Summary*  ({analysed}/{len(NIFTY_50)} analysed)",
        f"\U0001f7e2 Buy/Overweight: `{buy_count}`",
        f"\U0001f7e0 Hold: `{hold_count}`",
        f"\U0001f534 Sell/Underweight: `{sell_count}`",
    ]

    # Top BUY signals
    buys = [(t, s) for t, s in signals.items() if any(w in s.upper() for w in ["BUY", "OVERWEIGHT"])]
    if buys:
        lines.append("")
        lines.append("*\U0001f7e2 Top Buy Signals*")
        for t, s in buys[:5]:
            lines.append(_format_signal_row(t, s))

    # Top SELL signals
    sells = [(t, s) for t, s in signals.items() if any(w in s.upper() for w in ["SELL", "UNDERWEIGHT"])]
    if sells:
        lines.append("")
        lines.append("*\U0001f534 Top Sell Signals*")
        for t, s in sells[:5]:
            lines.append(_format_signal_row(t, s))

    # Full grid (compact)
    lines.append("")
    lines.append("*All Signals*")
    grid_lines = []
    for ticker, signal in sorted(signals.items()):
        if signal in ("Not analysed", "No data"):
            continue
        su = signal.upper()
        if "BUY" in su or "OVERWEIGHT" in su:
            e = "\U0001f7e2"
        elif "SELL" in su or "UNDERWEIGHT" in su:
            e = "\U0001f534"
        else:
            e = "\U0001f7e0"
        grid_lines.append(f"{e} `{ticker:<12}` {signal}")

    # Split into chunks to stay under 4000 chars
    chunk_size = 25
    for i in range(0, len(grid_lines), chunk_size):
        chunk = grid_lines[i:i+chunk_size]
        lines.append("\n".join(chunk))
        if i + chunk_size < len(grid_lines):
            lines.append("---")

    message = "\n".join(lines)

    # Send in chunks (Telegram max 4096 chars)
    CHUNK = 4000
    for i in range(0, len(message), CHUNK):
        ok = _telegram_send(message[i:i+CHUNK])
        if not ok:
            print(f"Failed to send chunk {i//CHUNK + 1}")
            return

    print(f"Morning brief sent — {analysed} stocks, {buy_count}B/{hold_count}H/{sell_count}S")


if __name__ == "__main__":
    main()
