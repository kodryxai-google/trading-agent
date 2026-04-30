"""Telegram delivery — send Kodryx AI signals via Telegram Bot API.
Sends a structured summary message + the full HTML report as a document attachment.
"""
import os
from pathlib import Path
from typing import Optional

import requests


def _bot_token() -> Optional[str]:
    return os.environ.get("TELEGRAM_BOT_TOKEN")


def _chat_id() -> Optional[str]:
    return os.environ.get("TELEGRAM_CHAT_ID")


def _is_configured() -> bool:
    return bool(_bot_token() and _chat_id())


def _send_document(file_path: str, caption: str = "") -> bool:
    """Send a file (HTML report) as a Telegram document attachment."""
    token = _bot_token()
    chat_id = _chat_id()
    if not token or not chat_id:
        return False
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendDocument",
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
                files={"document": (Path(file_path).name, f, "text/html")},
                timeout=30,
            )
        return r.status_code == 200 and r.json().get("ok")
    except Exception:
        return False


def _extract_key_stats(market_report: str) -> str:
    """Pull key stats from the market report."""
    lines = []
    for line in market_report.replace("<br>", "\n").split("\n"):
        stripped = line.strip().replace("*", "").replace("#", "").strip()
        if any(kw in stripped.lower() for kw in ["close price", "50-day sma", "200-day sma", "rsi", "macd", "death cross", "price:", "signal"]):
            if len(stripped) < 140:
                lines.append(f"\u2022 {stripped}")
        if len(lines) >= 6:
            break
    return "\n".join(lines) if lines else ""


def send_report_summary(
    ticker: str,
    trade_date: str,
    signal: str,
    market_report: str = "",
    report_path: Optional[str] = None,
) -> bool:
    """Send a summary message + the HTML report as a document attachment."""
    token = _bot_token()
    chat_id = _chat_id()
    if not token or not chat_id:
        return False

    su = signal.upper()
    if "BUY" in su:
        emoji = "\U0001f7e2"
    elif "SELL" in su:
        emoji = "\U0001f534"
    else:
        emoji = "\U0001f7e1"

    stats = _extract_key_stats(market_report)

    lines = [
        f"{emoji} *KODRYX AI — {ticker}  |  {trade_date}*",
        f"Signal: *{signal}*",
    ]
    if stats:
        lines.append("")
        lines.append(stats)

    message = "\n".join(lines)[:4000]

    # Step 1: send summary text
    ok_text = False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        ok_text = r.status_code == 200 and r.json().get("ok")
    except Exception:
        pass

    # Step 2: send HTML report as document
    ok_doc = False
    if report_path and Path(report_path).exists():
        ok_doc = _send_document(report_path, f"\U0001f4c4 Full Report — {ticker} {trade_date}")

        # Step 3: send CSV if exists
        csv_path = Path(report_path).with_suffix(".csv")
        if csv_path.exists():
            _send_document(str(csv_path), f"\U0001f4ca Trade CSV — {ticker} (import into Kite)")

    return ok_text or ok_doc


def send_signal(ticker: str, trade_date: str, signal: str, report_path: Optional[str] = None) -> bool:
    """Quick signal-only notification."""
    token = _bot_token()
    chat_id = _chat_id()
    if not token or not chat_id:
        return False

    su = signal.upper()
    emoji = {"BUY": "\U0001f7e2", "SELL": "\U0001f534"}.get(
        [w for w in ["BUY", "SELL"] if w in su][0] if any(w in su for w in ["BUY", "SELL"]) else "",
        "\U0001f7e1",
    )

    message = f"{emoji} *KODRYX AI — {ticker}*\nDate: {trade_date}\nSignal: *{signal}*"

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        return r.status_code == 200 and r.json().get("ok")
    except Exception:
        return False

