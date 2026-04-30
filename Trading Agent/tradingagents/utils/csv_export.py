"""Trade CSV export — generates Zerodha/Kite-compatible order basket file."""
import csv
import io
import re
from pathlib import Path
from typing import Optional


def _parse_recommendation(text: str) -> dict:
    """Extract action and quantity guidance from markdown decision text."""
    text_lower = text.lower()

    for keyword in ["sell", "underweight"]:
        if keyword in text_lower:
            action = "SELL"
            break
    else:
        for keyword in ["buy", "overweight"]:
            if keyword in text_lower:
                action = "BUY"
                break
        else:
            action = "HOLD"

    pct_match = re.search(r"(\d+)[\s\-]*%", text)
    if action in ("SELL", "BUY"):
        qty_pct = int(pct_match.group(1)) if pct_match else 25
    else:
        qty_pct = 0

    return {"action": action, "quantity_pct": qty_pct}


def generate_trade_csv(ticker: str, signal: str, decision_text: str) -> str:
    """Generate a CSV string for Zerodha/Kite basket import.

    Returns a CSV with: symbol, exchange, action, quantity_percent, confidence
    """
    rec = _parse_recommendation(decision_text or signal)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["symbol", "exchange", "action", "quantity_percent", "confidence"])
    writer.writerow([
        ticker.replace(".NS", "").replace(".BO", ""),
        "NSE",
        rec["action"],
        rec["quantity_pct"],
        "AI_MULTI_AGENT",
    ])
    return buf.getvalue()


def save_trade_csv(report_html_path: str, ticker: str, signal: str, decision_text: str) -> Optional[str]:
    """Save a trade CSV alongside the report and return its path."""
    csv_str = generate_trade_csv(ticker, signal, decision_text)
    csv_path = Path(report_html_path).with_suffix(".csv")
    csv_path.write_text(csv_str)
    return str(csv_path)
